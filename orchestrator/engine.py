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
    "never use markdown bullet points in casual conversation; "
    "when listing product recommendations always use • bullet points (one per product); "
    "CRITICAL — when recommending products, you MUST only reference the exact products and specs "
    "provided to you in the context. Never invent, assume, or add any detail not explicitly listed."
)

# ---------------------------------------------------------------------------
# Store-context cache — avoids one DB hit per message for the same tenant
# ---------------------------------------------------------------------------
_store_ctx_cache: Dict[str, str] = {}

def _get_store_context(tenant_id: str) -> str:
    """Return a one-line store context string for the given tenant, cached."""
    if not tenant_id or tenant_id == "default":
        return ""
    if tenant_id in _store_ctx_cache:
        return _store_ctx_cache[tenant_id]
    try:
        import portal.db as pdb  # local import to avoid circular-import at module load
        biz = pdb.get_business_by_id(tenant_id)
        if biz:
            ctx = (
                f"You are the shopping assistant for {biz.name} ({biz.website_url}). "
                f"Only recommend products that belong to this store's catalog."
            )
            _store_ctx_cache[tenant_id] = ctx
            return ctx
    except Exception as exc:
        logger.debug(f"Could not fetch store context for {tenant_id}: {exc}")
    _store_ctx_cache[tenant_id] = ""
    return ""

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
                    tenant_id=query_input.tenant_id,
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
            # Phi-3's confidence guide: 0.8-1.0 = clear product query,
            # 0.5-0.7 = needs inference, 0.2-0.4 = ambiguous/non-product.
            # Treat anything below 0.5 with no concrete entities as chat.
            is_pure_chat = (
                understanding.confidence < 0.5
                and not understanding.entities.get("features")
                and not understanding.constraints.get("category")
                and not understanding.constraints.get("brand")
            )
            if is_pure_chat:
                reply = await self._chat_reply(
                    query_input.query_text, products=[],
                    chat_history=query_input.chat_history,
                    session_id=query_input.session_id,
                    tenant_id=query_input.tenant_id,
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

            # STEP 5: Generate a natural language reply.
            # When a comparison was produced, skip the LLM call — fixed intro only,
            # no follow-up question; the table speaks for itself.
            is_vague = self._is_vague_product_query(understanding)
            if results.get("comparison"):
                chat_reply = "Here\u2019s a side-by-side comparison for you!"
            else:
                chat_reply = await self._chat_reply(
                    query_input.query_text, products=ranked[:3],
                    chat_history=query_input.chat_history,
                    session_id=query_input.session_id,
                    is_vague=is_vague,                    tenant_id=query_input.tenant_id,                )

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

        # Strip punctuation from each word for reliable matching
        clean_words = [w.strip("!?.,:'\"") for w in t.split()]

        PRODUCT_HINTS = {
            "buy", "show", "find", "search", "recommend", "compare", "best",
            "cheap", "price", "under", "top", "rated", "product", "item",
            "jacket", "shirt", "phone", "laptop", "watch", "bag", "shoes",
            "dress", "ring", "necklace", "headphone", "earphone", "charger",
            "suit", "coat", "jeans", "pants", "skirt", "blouse", "hoodie",
        }
        has_product_hint = any(w in PRODUCT_HINTS for w in clean_words)

        # Rule 1: Exact full-phrase matches (any length)
        EXACT = {
            "hi", "hello", "hey", "hiya", "howdy", "sup", "yo", "helo", "hii", "hiii",
            "good morning", "good afternoon", "good evening", "good night",
            "how are you", "how r u", "hows it going", "how's it going",
            "what's up", "whats up", "who are you", "what are you",
            "what can you do", "help", "thanks", "thank you", "bye", "goodbye",
            "ok", "okay", "cool", "nice", "great", "awesome", "perfect", "sure",
            "sounds good", "that's great", "that's nice", "that's cool", "that's perfect",
            "i see", "got it", "makes sense", "i like it", "i love it", "love it",
            "not bad", "looks good", "looks great", "looks nice", "that works",
            "never mind", "no thanks", "that's all", "i'm good", "im good",
        }
        if t in EXACT:
            return True

        # Rule 2: Message STARTS with a greeting word and has NO product hints anywhere.
        # Catches "Hi, how are you? Can we start?", "Hello! Tell me more.", etc.
        GREETING_STARTS = {"hi", "hello", "hey", "hiya", "howdy", "yo", "sup", "helo"}
        if clean_words and clean_words[0] in GREETING_STARTS and not has_product_hint:
            return True

        # Rule 3: Short messages (≤ 3 words) with no product hints
        if len(clean_words) <= 3 and not has_product_hint:
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
        tenant_id: str = "",
    ) -> str:
        """
        Generate a warm, conversational Quiribot reply using the consistent persona.
        Includes full chat history and live session context so each turn is coherent.
        When is_vague=True and products are shown, appends ONE follow-up question
        (capped at 2 total across the whole conversation).
        """
        session_ctx = self._build_session_context(session_id)
        store_ctx   = _get_store_context(tenant_id)

        system_content = QUIRIBOT_PERSONA
        if store_ctx:
            system_content = store_ctx + " " + system_content
        if session_ctx:
            system_content += f"\n\nCustomer context this session:\n{session_ctx}"

        prior_followups   = self._count_prior_followups(chat_history)
        user_messages     = sum(1 for m in (chat_history or []) if m.get("role") == "user")
        allowed_followups = (user_messages // 4) + 1
        add_followup      = is_vague and prior_followups < allowed_followups

        if products:
            product_blocks = []
            for i, p in enumerate(products, 1):
                meta = p.metadata if hasattr(p, "metadata") else p.get("metadata", {})
                name  = meta.get("name", p.product_id if hasattr(p, "product_id") else "?")
                price = meta.get("price", "?")
                rating = meta.get("rating", "?")
                desc  = meta.get("description", "")
                # Use the last line of description (the spec summary) if available,
                # otherwise fall back to the first 120 chars of the full description.
                spec_line = ""
                if desc:
                    lines = [l.strip() for l in desc.strip().splitlines() if l.strip()]
                    # Last line usually contains "Processor: ... | RAM: ... | Storage: ..."
                    last = lines[-1] if lines else ""
                    spec_line = last if last.startswith("Processor:") else desc[:120]
                block = (
                    f"Product {i}: {name}\n"
                    f"  Price: Rs. {price} | Rating: {rating}/5\n"
                )
                if spec_line:
                    block += f"  Key specs: {spec_line}\n"
                product_blocks.append(block)
            product_summary = "\n".join(product_blocks)
            n = len(products)
            if add_followup:
                user_content = (
                    f"The customer asked: \"{query}\"\n\n"
                    f"You found {n} product(s) — use ONLY these details, nothing else:\n"
                    f"{product_summary}\n"
                    f"Reply format (follow exactly):\n"
                    f"One short intro sentence — do NOT state how many products there are.\n"
                    f"Then one • bullet per product:\n"
                    f"  • [Short product name] — [single reason it fits, max 8 words]\n"
                    f"Then on a SEPARATE new line: ONE follow-up question (max 10 words).\n"
                    f"Total reply under 60 words. No semicolons."
                )
            else:
                user_content = (
                    f"The customer asked: \"{query}\"\n\n"
                    f"You found {n} product(s) — use ONLY these details, nothing else:\n"
                    f"{product_summary}\n"
                    f"Reply format (follow exactly):\n"
                    f"One short intro sentence — do NOT state how many products there are.\n"
                    f"Then one • bullet per product:\n"
                    f"  • [Short product name] — [single reason it fits, max 8 words]\n"
                    f"Total reply under 50 words. No questions. No semicolons."
                )
        else:
            user_content = query

        messages = self._build_llm_messages(system_content, user_content, chat_history or [])
        # Allow more tokens when products are present so per-product explanations aren't cut off
        max_tok = 320 if products else 180
        try:
            result = await llm_client.chat_completion(messages, temperature=0.8, max_tokens=max_tok)
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
                    results["comparison"] = await self._run_comparison(products_for_comparison[:3], understanding)
                    # Ensure product cards appear in the widget even when comparison
                    # ran off session-history fallback (ranked_products may be empty)
                    if not results.get("ranked_products"):
                        results["ranked_products"] = products_for_comparison
                    
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