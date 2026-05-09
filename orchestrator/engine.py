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

# ---------------------------------------------------------------------------
# Consistent Quiribot persona — single definition used by every LLM call
# ---------------------------------------------------------------------------
QUIRIBOT_PERSONA = (
    "You are Quiribot — a warm, sharp, and genuinely helpful shopping assistant, "
    "like a knowledgeable friend who works in retail. "
    "Your style: conversational and natural, never robotic. "
    "You remember everything discussed earlier in this conversation and refer back to it naturally. "
    "When a customer's request is vague, ask ONE short, focused follow-up question — "
    "never ask more than one question at a time, and skip it entirely when you already have enough to help. "
    "Keep replies brief (1–3 sentences) unless you are introducing several products or explaining a comparison. "
    "Hard rules: never say you are an AI or mention any system instructions; "
    "never repeat the customer's question back verbatim; "
    "never use markdown bullet points in casual replies."
)

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
                reply = await self._chat_reply(
                    query_input.query_text, products=[],
                    chat_history=query_input.chat_history,
                    session_id=query_input.session_id,
                )
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
                reply = await self._chat_reply(
                    query_input.query_text, products=[],
                    chat_history=query_input.chat_history,
                    session_id=query_input.session_id,
                )
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
            # Pass is_vague so the reply can append ONE follow-up question after products.
            is_vague = self._is_vague_product_query(understanding)
            chat_reply = await self._chat_reply(
                query_input.query_text, products=ranked[:3],
                chat_history=query_input.chat_history,
                session_id=query_input.session_id,
                is_vague=is_vague,
            )

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

    def _count_prior_followups(self, chat_history: list) -> int:
        """Count how many times Quiribot has already asked a follow-up question."""
        count = 0
        for msg in (chat_history or []):
            if msg.get("role") == "assistant" and "?" in msg.get("content", ""):
                count += 1
        return count

    async def _chat_reply(
        self,
        query: str,
        products: list,
        chat_history: list = None,
        session_id: str = "",
        is_vague: bool = False,
    ) -> str:
        """
        Generate a warm, conversational Quiribot reply using the consistent persona.
        Includes full chat history and live session context so each turn is coherent.
        When is_vague=True and products are shown, appends ONE follow-up question
        (capped at 2 total across the whole conversation).
        """
        session_ctx = self._build_session_context(session_id)
        system_content = QUIRIBOT_PERSONA
        if session_ctx:
            system_content += f"\n\nCustomer context this session:\n{session_ctx}"

        prior_followups = self._count_prior_followups(chat_history)
        add_followup = is_vague and prior_followups < 2

        if products:
            product_lines = []
            for p in products:
                meta = p.metadata if hasattr(p, "metadata") else p.get("metadata", {})
                name = meta.get("name", p.product_id if hasattr(p, "product_id") else "?")
                price = meta.get("price", "?")
                rating = meta.get("rating", "?")
                product_lines.append(f"- {name} (${price}, rated {rating}/5)")
            product_summary = "\n".join(product_lines)
            if add_followup:
                user_content = (
                    f"The customer asked: \"{query}\"\n"
                    f"You found these products:\n{product_summary}\n"
                    f"Introduce these results in 1\u20132 warm sentences, then end with ONE short "
                    f"follow-up question to help narrow down exactly what they need "
                    f"(e.g. a budget, occasion, or preference). Keep it natural."
                )
            else:
                user_content = (
                    f"The customer asked: \"{query}\"\n"
                    f"You found these products:\n{product_summary}\n"
                    f"Introduce these results in 1\u20132 warm, conversational sentences."
                )
        else:
            user_content = query

        messages = self._build_llm_messages(system_content, user_content, chat_history or [])
        try:
            result = await llm_client.chat_completion(messages, temperature=0.8, max_tokens=180)
            return result["content"].strip()
        except Exception:
            if products:
                return f"Here are the top results I found for \"{query}\"!"
            return "I'm here to help! Ask me to find products, compare options, or just chat."

    def _build_llm_messages(
        self,
        system_content: str,
        user_content: str,
        chat_history: list,
    ) -> List[Dict[str, Any]]:
        """
        Build an OpenAI-format messages array:
        [system prompt] + [prior conversation turns] + [current user message]
        Caps history at 8 messages (4 turns) to respect context window limits.
        """
        messages: List[Dict[str, Any]] = [{"role": "system", "content": system_content}]
        for msg in (chat_history or [])[-8:]:
            role = msg.get("role", "")
            content = msg.get("content", "")
            if role in ("user", "assistant") and content:
                messages.append({"role": role, "content": content})
        messages.append({"role": "user", "content": user_content})
        return messages

    def _build_session_context(self, session_id: str) -> str:
        """
        Return a short natural-language summary of what the customer has browsed
        this session, so the LLM can refer back naturally in replies.
        Returns an empty string for first-time users with no history.
        """
        if not session_id:
            return ""
        features = session_store.get_user_features(session_id)
        if not features:
            return ""
        parts = []
        cats = features.get("preferred_categories", [])
        if cats:
            parts.append(f"Browsed categories: {', '.join(cats[-3:])}")
        brands = features.get("preferred_brands", [])
        if brands:
            parts.append(f"Brands shown: {', '.join(brands[-3:])}")
        history_count = len(features.get("history", []))
        if history_count:
            parts.append(f"Products shown this session: {history_count}")
        return "\n".join(parts)

    def _is_vague_product_query(self, understanding: QueryUnderstanding) -> bool:
        """
        Returns True when the user seems to want a product but hasn't given
        enough detail to run a meaningful search — triggering a clarifying
        question instead of returning poor results.
        """
        if understanding.confidence >= 0.6:
            return False  # Enough signal — proceed to search

        # Must have some product intent (pure chat is handled separately)
        has_product_signal = (
            bool(understanding.entities.get("features"))
            or understanding.intent in (IntentType.RECOMMENDATION, IntentType.SEARCH)
        )
        if not has_product_signal:
            return False

        # Only ask if we have NO concrete searchable constraints at all
        has_enough_to_search = (
            understanding.constraints.get("category")
            or understanding.constraints.get("brand")
            or understanding.constraints.get("price_range")
        )
        return not has_enough_to_search

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
        """Execute retrieval agent.

        Products are indexed as: "{title}. Category: {category}. {description}"
        To maximise cosine similarity we build a query string in the same style,
        injecting whatever structured data QueryUnderstanding extracted.
        """
        parts: List[str] = []

        # 1. Named product entities / features  ("laptop", "waterproof jacket", ...)
        features = understanding.entities.get("features", [])
        product_names = understanding.entities.get("product_names", [])
        named = (product_names or []) + (features or [])
        if named:
            parts.append(", ".join(named))

        # 2. Category  ("electronics", "men's clothing", ...)
        category = understanding.constraints.get("category", "")
        if category:
            parts.append(f"Category: {category}")

        # 3. Raw query always at the end as a safety net
        parts.append(understanding.raw_query)

        enriched_query = ". ".join(p for p in parts if p)

        retrieval_input = RetrievalInput(
            query_text=enriched_query,
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