from pydantic import BaseModel, Field, field_validator, model_validator
from typing import List, Optional, Any, Dict

class LLMRequest(BaseModel):
    messages: List[Dict[str, str]]
    temperature: Optional[float] = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(default=512, ge=1)

class LLMResponse(BaseModel):
    text: str
    usage: Optional[Dict[str, Any]] = None

class TextEmbedRequest(BaseModel):
    text: str = Field(..., min_length=1)

class EmbedResponse(BaseModel):
    vector: List[float]

class VectorAddRequest(BaseModel):
    vectors: List[List[float]] = Field(..., min_length=1)
    metadata: List[Dict[str, Any]]

    @model_validator(mode="after")
    def vectors_and_metadata_same_length(self) -> "VectorAddRequest":
        if len(self.vectors) != len(self.metadata):
            raise ValueError(
                f"vectors length ({len(self.vectors)}) must equal "
                f"metadata length ({len(self.metadata)})."
            )
        return self

class VectorSearchRequest(BaseModel):
    vector: List[float] = Field(..., min_length=1)
    k: int = Field(default=4, ge=1, le=1000)
    filters: Optional[Dict[str, Any]] = None

class SearchResult(BaseModel):
    score: float
    metadata: Dict[str, Any]

class SearchResponse(BaseModel):
    results: List[SearchResult]