from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from enum import Enum
from datetime import datetime

# ============================================================================
# Query Understanding
# ============================================================================

class IntentType(str, Enum):
    SEARCH = "search"
    RECOMMENDATION = "recommendation"
    COMPARISON = "comparison"
    EXPLANATION = "explanation"
    CROSS_SELL = "cross_sell"

class PreprocessingResult(BaseModel):
    """Output of the query preprocessing pipeline, attached to QueryInput."""
    original_query: str
    cleaned_query: str
    normalized_query: str
    price_hints: Dict[str, Any] = {}
    detected_brands: List[str] = []
    detected_categories: List[str] = []
    is_valid: bool = True
    warnings: List[str] = []


class CommentPreprocessingResult(BaseModel):
    """Output of the comment/review preprocessing pipeline."""
    original_text: str
    normalized_text: str
    detected_brands: List[str] = []
    is_valid: bool = True
    warnings: List[str] = []


class QueryInput(BaseModel):
    query_text: str = Field(..., min_length=1)
    user_id: Optional[str] = None
    session_id: str
    tenant_id: str = "default"
    preprocessing: Optional["PreprocessingResult"] = None
    # Text-only prior turns sent by the UI each request; session-scoped (cleared on new chat)
    chat_history: List[Dict[str, str]] = []

class QueryUnderstanding(BaseModel):
    intent: IntentType
    requires_comparison: bool = False
    requires_cross_sell: bool = False
    requires_personalization: bool = False
    constraints: Dict[str, Any] = {}
    entities: Dict[str, Any] = {}
    confidence: float = Field(..., ge=0.0, le=1.0)
    raw_query: str

# ============================================================================
# Retrieval
# ============================================================================

class RetrievalInput(BaseModel):
    query_text: str
    query_embedding: Optional[List[float]] = None
    image_path: Optional[str] = None
    filters: Dict[str, Any]
    top_k: int = 20
    tenant_id: str

class RetrievalResult(BaseModel):
    product_id: str
    similarity_score: float = Field(..., ge=0.0, le=1.0)
    source_type: str  # "description" | "image" | "reviews"
    timestamp: str
    metadata: Dict[str, Any]

class RetrievalOutput(BaseModel):
    results: List[RetrievalResult]
    total_candidates: int
    retrieval_time_ms: float

# ============================================================================
# Ranking
# ============================================================================

class RankingInput(BaseModel):
    retrieval_results: List[RetrievalResult]
    user_features: Optional[Dict[str, Any]] = None
    constraints: Dict[str, Any] = {}   # actual constraint values from query understanding
    weights: Optional[Dict[str, float]] = None

class ScoringBreakdown(BaseModel):
    relevance_score: float
    constraint_match_score: float
    rating_score: float
    personalization_score: float
    stock_priority_score: float
    final_score: float

class RankedProduct(BaseModel):
    product_id: str
    rank: int
    scoring: ScoringBreakdown
    metadata: Dict[str, Any]

class RankingOutput(BaseModel):
    ranked_products: List[RankedProduct]
    weights_used: Dict[str, float]

# ============================================================================
# Comparison
# ============================================================================

class ComparisonInput(BaseModel):
    product_ids: List[str] = Field(..., min_length=2, max_length=5)
    attributes_to_compare: List[str]

class ComparisonTable(BaseModel):
    headers: List[str]
    rows: List[Dict[str, Any]]

class ComparisonOutput(BaseModel):
    comparison_table: ComparisonTable
    narrative_summary: str
    products_compared: List[str]

# ============================================================================
# Explainability
# ============================================================================

class ExplainabilityInput(BaseModel):
    ranked_products: List[RankedProduct]
    top_n: int = 3
    query_context: str
    evidence_sources: List[Dict[str, Any]]

class Explanation(BaseModel):
    product_id: str
    summary: str
    reasons: List[str]
    citations: List[str]

class ExplainabilityOutput(BaseModel):
    explanations: List[Explanation]

# ============================================================================
# MBA
# ============================================================================

class MBAInput(BaseModel):
    current_product_id: str
    user_history: Optional[List[str]] = None
    max_recommendations: int = 5

class CrossSellItem(BaseModel):
    product_id: str
    confidence: float
    support: float
    rule_type: str

class MBAOutput(BaseModel):
    cross_sell_items: List[CrossSellItem]
    rules_applied: int

# ============================================================================
# Orchestrator
# ============================================================================

class ExecutionPlan(BaseModel):
    """Deterministic execution plan built by orchestrator."""
    request_id: str
    steps: List[str]  # Agent names in execution order
    timeout_ms: int
    fallback_enabled: bool = True

class OrchestratorOutput(BaseModel):
    """Final aggregated response from orchestrator."""
    request_id: str
    intent: IntentType
    ranked_products: List[RankedProduct]
    explanations: Optional[ExplainabilityOutput] = None
    comparison: Optional[ComparisonOutput] = None
    cross_sell: Optional[MBAOutput] = None
    conversational_reply: Optional[str] = None
    execution_time_ms: float
    errors: List[str] = []