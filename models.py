"""
Pydantic models for API requests and responses
Phase 1: Simplified entity-impact mapping
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Literal
from datetime import datetime


class EntityImpact(BaseModel):
    """Impact assessment for a single entity (currency)"""
    currency: str = Field(..., description="Currency pair (e.g., GBP, EURUSD)")
    confidence: Literal["high", "medium", "low"] = Field(..., description="Confidence level")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Numeric confidence score")
    reasoning: str = Field(..., description="Explanation of why this entity is impacted")


class NewsAnalysisRequest(BaseModel):
    """Request model for news analysis"""
    headline: str = Field(..., min_length=10, description="News headline to analyze")
    target_entities: Optional[List[str]] = Field(None, description="Specific entities to analyze (optional)")
    min_confidence: Optional[float] = Field(0.3, ge=0.0, le=1.0, description="Minimum confidence threshold")
    llm_provider: Optional[Literal["mock", "gemini_flash", "claude"]] = Field("mock", description="LLM provider to use")


class NewsAnalysisResponse(BaseModel):
    """Response model for news analysis - Phase 1 simplified format"""
    headline: str
    impacted_entities: List[EntityImpact]
    processing_time_ms: float
    analysis_timestamp: datetime
    metadata: Optional[dict] = None


class HealthCheckResponse(BaseModel):
    """Health check response"""
    status: str
    version: str
    environment: str
    model_provider: str


class BatchAnalysisRequest(BaseModel):
    """Request model for batch analysis"""
    headlines: List[str] = Field(..., min_items=1, max_items=100)
    min_confidence: Optional[float] = Field(0.3, ge=0.0, le=1.0)


class BatchAnalysisResponse(BaseModel):
    """Response model for batch analysis"""
    results: List[NewsAnalysisResponse]
    total_processed: int
    total_processing_time_ms: float
