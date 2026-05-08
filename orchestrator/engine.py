from models.schemas import (
    QueryInput, QueryUnderstanding, ExecutionPlan, OrchestratorOutput,
    RetrievalInput, RankingInput, ComparisonInput, ExplainabilityInput, MBAInput,
    RankedProduct, ScoringBreakdown, IntentType
)
from agents.query_understanding import query_understanding_agent
from agents.retrieval import retrieval_agent
from agents.ranking import ranking_agent
from agents.comparison import comparison_agent
from agents.explainability import explainability_agent
from agents.mba import mba_agent
from services.llm_client import llm_client
from services.session_store import session_store
from config.settings import settings
import logging
import time
import uuid
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

class Orchestrator:
    """
    Deterministic policy engine for agent execution.
    
    NO LLM INVOLVEMENT.
    Pure Python control flow.
    """
    
    def __init__(self):
        self.timeout = settings.ORCHESTRATOR_TIMEOUT
        self.confidence_threshold = settings.CONFIDENCE_THRESHOLD
        
    async def execute(self, query_input: QueryInput) -> OrchestratorOutput:
        start_time = time.time()
        request_id = str(uuid.uuid4())
        errors = []

        logger.info(f"[{request_id}] Orchestrating query: {query_input.query_text}")

        try:
            # STEP 0: Fast keyword check — no LLM cost for pure conversation
            if self._is_conversational(query_input.query_text):
                reply = await self._chat_reply(query_input.query_text, products=[])
                return OrchestratorOutput(
                    request_id=request_id,
                    intent=IntentType.SEARCH,
                    ranked_products=[],
                    conversational_reply=reply,
                    execution_time_ms=(time.time() - start_time) * 1000,
                    errors=[]
                )

            # STEP 1: Query Understanding
            understanding = await query_understanding_agent.understand(query_input)

            # STEP 2: Pure-conversation shortcut
            # If confidence is low AND no product entities were found, the user
            # is just chatting — let the LLM reply freely without any search.
            is_pure_chat = (
                understanding.confidence < self.confidence_threshold
                and not understanding.entities.get("features")
                and not understanding.constraints.get("category")
                and not understanding.constraints.get("brand")
            )
            if is_pure_chat:
                reply = await self._chat_reply(query_input.query_text, products=[])
                return OrchestratorOutput(
                    request_id=request_id,
                    intent=IntentType.SEARCH,
                    ranked_products=[],
                    conversational_reply=reply,
                    execution_time_ms=(time.time() - start_time) * 1000,
                    errors=[]
                )

            # STEP 3: Build Execution Plan
            plan = self._build_plan(understanding)
            logger.info(f"Execution plan: {plan.steps}")

            # STEP 4: Execute Agents
            results = await self._execute_plan(plan, understanding, query_input, errors)

            ranked = results.get("ranked_products", [])

            # STEP 5: Always generate a natural language reply from the LLM
            # It either introduces the products found or handles the query conversationally.
            chat_reply = await self._chat_reply(query_input.query_text, products=ranked[:3])

            # STEP 6: Update session with results from this turn
            if ranked and query_input.session_id:
                session_store.update_after_response(query_input.session_id, ranked)

            # STEP 7: Aggregate Output
            execution_time = (time.time() - start_time) * 1000

            return OrchestratorOutput(
                request_id=request_id,
                intent=understanding.intent,
                ranked_products=ranked,
                explanations=results.get("explanations"),
                comparison=results.get("comparison"),
                cross_sell=results.get("cross_sell"),
                conversational_reply=chat_reply,
                execution_time_ms=execution_time,
                errors=errors
            )

        except Exception as e:
            logger.error(f"Orchestration failed: {e}")
            return OrchestratorOutput(
                request_id=request_id,
                intent=understanding.intent if 'understanding' in locals() else IntentType.SEARCH,
                ranked_products=[],
                execution_time_ms=(time.time() - start_time) * 1000,
                errors=[str(e)]
            )
            
    def _is_conversational(self, text: str) -> bool:
        """
        Fast keyword check — no LLM call.
        Catches greetings and non-product messages before wasting a query-understanding call.
        """
        t = text.lower().strip().rstrip("!?.,:")
        # Exact matches
        EXACT = {
            "hi", "hello", "hey", "hiya", "howdy", "sup", "yo", "helo", "hii", "hiii",
            "good morning", "good afternoon", "good evening", "good night",
            "how are you", "how r u", "hows it going", "how's it going",
            "what's up", "whats up", "who are you", "what are you",
            "what can you do", "help", "thanks", "thank you", "bye", "goodbye",
            "ok", "okay", "cool", "nice", "great", "awesome",
        }
        if t in EXACT:
            return True
        # Short single-word inputs with no product keywords are chat
        words = t.split()
        PRODUCT_HINTS = {
            "buy", "show", "find", "search", "recommend", "compare", "best",
            "cheap", "price", "under", "top", "rated", "product", "item",
            "jacket", "shirt", "phone", "laptop", "watch",
        }
        if len(words) <= 2 and not any(w in PRODUCT_HINTS for w in words):
            return True
        return False

    async def _conversational_reply(self, text: str) -> str:
        """Generate a friendly conversational response via LLM."""
        messages = [
            {"role": "system", "content": (
                "You are Quiribot, a friendly e-commerce shopping assistant. "
                "You help users find products, compare items, and get recommendations. "
                "Keep replies short and friendly. "
                "If greeted, introduce yourself briefly and invite the user to search for products."
            )},
            {"role": "user", "content": text},
        ]
        try:
            result = await llm_client.chat_completion(messages, temperature=0.7, max_tokens=120)
            return result["content"].strip()
        except Exception:
            return (
                "Hi! I'm Quiribot, your shopping assistant. "
                "Ask me to find products, compare items, or give recommendations!"
            )

    async def _chat_reply(self, query: str, products: list) -> str:
        """
        Generate a natural ChatGPT-style reply for any query.
        If products were found, introduce them conversationally.
        If no products, respond helpfully to whatever the user said.
        """
        if products:
            product_lines = []
            for p in products:
                meta = p.metadata if hasattr(p, 'metadata') else p.get('metadata', {})
                name = meta.get('name', p.product_id if hasattr(p, 'product_id') else '?')
                price = meta.get('price', '?')
                rating = meta.get('rating', '?')
                product_lines.append(f"- {name} (${price}, rated {rating}/5)")
            product_summary = "\n".join(product_lines)
            user_content = (
                f"The user asked: \"{query}\"\n"
                f"I found these products:\n{product_summary}\n"
                f"Write a short, friendly 1-2 sentence intro for these results."
            )
        else:
            user_content = query

        messages = [
            {"role": "system", "content": (
                "You are Quiribot, a helpful and friendly shopping assistant — like a knowledgeable friend. "
                "You can answer any question naturally. "
                "When introducing product results, be warm and conversational (1-2 sentences max). "
                "When there are no products, just chat naturally — answer the question, give your opinion, or ask what they're looking for. "
                "Never say you are an AI or mention any rules. Never be robotic or formal."
            )},
            {"role": "user", "content": user_content},
        ]
        try:
            result = await llm_client.chat_completion(messages, temperature=0.8, max_tokens=150)
            return result["content"].strip()
        except Exception:
            if products:
                return f"Here are the top results I found for \u201c{query}\u201d!"
            return "I'm here to help! Ask me to find products, compare options, or just chat."

    def _build_plan(self, understanding: QueryUnderstanding) -> ExecutionPlan:
        steps = ["retrieval", "ranking"]

        if understanding.requires_comparison or understanding.intent == IntentType.COMPARISON:
            steps.append("comparison")

        if understanding.requires_cross_sell:
            steps.append("mba")

        # NOTE: explainability is intentionally excluded — _chat_reply covers it
        # in a single LLM call instead of one call per product.

        return ExecutionPlan(
            request_id=str(uuid.uuid4()),
            steps=steps,
            timeout_ms=self.timeout * 1000,
            fallback_enabled=True
        )
        
    async def _execute_plan(
        self,
        plan: ExecutionPlan,
        understanding: QueryUnderstanding,
        query_input: QueryInput,
        errors: list
    ) -> Dict[str, Any]:
        """
        Execute agents sequentially according to plan.
        """
        results = {}

        # Load accumulated session features for this request
        user_features = session_store.get_user_features(query_input.session_id)
        user_history = session_store.get_viewed_product_ids(query_input.session_id)

        for step in plan.steps:
            try:
                if step == "retrieval":
                    results["retrieval"] = await self._run_retrieval(understanding, query_input)
                    if not results["retrieval"].results:
                        logger.warning("Retrieval returned 0 results.")
                        errors.append(
                            "No products found matching your query. "
                            "Try different keywords or remove filters."
                        )
                    
                elif step == "ranking":
                    if "retrieval" not in results or not results["retrieval"].results:
                        logger.warning("Skipping ranking - no retrieval results")
                        continue
                    results["ranking"] = self._run_ranking(
                        results["retrieval"], understanding, query_input, user_features
                    )
                    results["ranked_products"] = results["ranking"].ranked_products
                    
                elif step == "comparison":
                    products_for_comparison = results.get("ranked_products", [])
                    if len(products_for_comparison) < 2:
                        # Fallback: use the top products from the previous turn
                        stored_dicts = session_store.get_last_ranked_products(query_input.session_id)
                        if len(stored_dicts) >= 2:
                            products_for_comparison = [
                                RankedProduct(
                                    product_id=d["product_id"],
                                    rank=d["rank"],
                                    metadata=d["metadata"],
                                    scoring=ScoringBreakdown(**d["scoring"]),
                                )
                                for d in stored_dicts
                            ]
                            logger.info(
                                f"Comparison fallback: using {len(products_for_comparison)} "
                                "products from session history"
                            )
                    if len(products_for_comparison) < 2:
                        logger.warning("Skipping comparison - need at least 2 products")
                        continue
                    results["comparison"] = await self._run_comparison(products_for_comparison[:5], understanding)
                    
                elif step == "explainability":
                    if "ranked_products" not in results:
                        logger.warning("Skipping explainability - no ranked products")
                        continue
                    results["explanations"] = await self._run_explainability(
                        results["ranked_products"],
                        understanding.raw_query
                    )
                    
                elif step == "mba":
                    if "ranked_products" not in results or not results["ranked_products"]:
                        logger.warning("Skipping MBA - no products")
                        continue
                    top_product = results["ranked_products"][0]
                    results["cross_sell"] = self._run_mba(
                        top_product.product_id, query_input, user_history
                    )
                    
            except Exception as e:
                logger.error(f"Agent {step} failed: {e}")
                # Continue with next agent (fallback strategy)
                continue
                
        return results
        
    async def _run_retrieval(
        self,
        understanding: QueryUnderstanding,
        query_input: QueryInput
    ):
        """Execute retrieval agent."""
        retrieval_input = RetrievalInput(
            query_text=understanding.raw_query,
            filters=understanding.constraints,
            top_k=settings.DEFAULT_TOP_K,
            tenant_id=query_input.tenant_id
        )
        return await retrieval_agent.retrieve(retrieval_input)
        
    def _run_ranking(
        self,
        retrieval_output,
        understanding: QueryUnderstanding,
        query_input: QueryInput,
        user_features: Optional[Dict[str, Any]] = None,
    ):
        """Execute ranking agent with accumulated session preferences."""
        ranking_input = RankingInput(
            retrieval_results=retrieval_output.results,
            user_features=user_features,
            constraints=understanding.constraints
        )
        return ranking_agent.rank(ranking_input)
        
    async def _run_comparison(self, ranked_products, understanding: QueryUnderstanding = None):
        """Execute comparison agent."""
        product_ids = [p.product_id for p in ranked_products]
        product_data = [p.metadata for p in ranked_products]
        attributes = self._derive_comparison_attributes(ranked_products, understanding)
        comparison_input = ComparisonInput(
            product_ids=product_ids,
            attributes_to_compare=attributes
        )
        return await comparison_agent.compare(comparison_input, product_data)

    def _derive_comparison_attributes(
        self,
        ranked_products,
        understanding: QueryUnderstanding = None
    ) -> List[str]:
        """
        Select comparison attributes relevant to the detected product category.
        Falls back to universal attributes for unknown categories.
        """
        # Base attributes always meaningful
        attrs: List[str] = ["price", "rating", "brand"]

        # Resolve category from constraints first, then from product metadata
        category = ""
        if understanding and "category" in understanding.constraints:
            category = understanding.constraints["category"].lower()
        elif ranked_products:
            category = ranked_products[0].metadata.get("category", "").lower()

        _ELECTRONICS = {
            "smartphone", "laptop", "tablet", "television", "smart television",
            "headphones", "earphones", "smartwatch", "camera", "computer",
            "monitor", "keyboard", "mouse", "printer", "router", "speaker",
        }
        _FASHION = {
            "clothing", "apparel", "footwear", "shoes", "sneakers", "boots",
            "shirt", "t-shirt", "dress", "jeans", "jacket", "hoodie",
            "trousers", "shorts", "sandals", "outerwear", "handbag",
            "bags", "activewear", "watch", "eyewear", "accessories",
        }
        _FURNITURE = {
            "sofa", "chair", "table", "furniture", "bed", "wardrobe",
            "bookshelf", "shelf", "mattress", "dining furniture", "desk",
            "nightstand", "dresser", "coffee table",
        }
        _APPLIANCES = {
            "refrigerator", "washing machine", "air conditioner", "microwave",
            "kettle", "vacuum cleaner", "freezer", "heater", "fan",
            "kitchen appliance", "water dispenser",
        }

        if any(c in category for c in _ELECTRONICS):
            attrs += ["screen_size", "battery", "storage", "ram"]
        elif any(c in category for c in _FASHION):
            attrs += ["size", "material", "color", "fit"]
        elif any(c in category for c in _FURNITURE):
            attrs += ["dimensions", "material", "color", "weight_capacity"]
        elif any(c in category for c in _APPLIANCES):
            attrs += ["capacity", "power", "warranty"]
        else:
            # Unknown category: add any canonical attribute present in all products
            if ranked_products:
                from agents.comparison import comparison_agent as ca
                canonical = set(ca.CANONICAL_ATTRIBUTES.keys())
                common_keys: set = set(ranked_products[0].metadata.keys())
                for p in ranked_products[1:]:
                    common_keys &= set(p.metadata.keys())
                extra = (common_keys & canonical) - set(attrs)
                attrs += sorted(extra)

        return attrs
        
    async def _run_explainability(self, ranked_products, query_context: str):
        """Execute explainability agent."""
        explainability_input = ExplainabilityInput(
            ranked_products=ranked_products,
            top_n=3,
            query_context=query_context,
            evidence_sources=[]  # TODO: Fetch reviews/specs
        )
        return await explainability_agent.explain(explainability_input)
        
    def _run_mba(
        self,
        product_id: str,
        query_input: QueryInput,
        user_history: Optional[List[str]] = None,
    ):
        """Execute MBA agent, excluding products already seen by this user."""
        mba_input = MBAInput(
            current_product_id=product_id,
            user_history=user_history or [],
            max_recommendations=5
        )
        return mba_agent.recommend(mba_input)
        
    def _extract_constraint_flags(self, understanding: QueryUnderstanding) -> Dict[str, bool]:
        """Legacy helper — kept for compatibility. Constraints are now passed directly."""
        return {}

# Global instance
orchestrator = Orchestrator()