from pydantic import BaseModel, Field, validator
from typing import List, Optional
from datetime import datetime
from enum import Enum


class CurrencyCode(str, Enum):
    """Supported currency codes"""
    USD = "USD"
    EUR = "EUR"
    GBP = "GBP"
    JPY = "JPY"
    AUD = "AUD"
    CAD = "CAD"
    CHF = "CHF"
    NZD = "NZD"
    CNY = "CNY"


class CurrencyImpact(BaseModel):
    """Impact assessment for a single currency"""
    currency: CurrencyCode
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence score 0-1")
    reasoning: str = Field(min_length=10, description="Brief explanation of impact")

    @validator('confidence')
    def round_confidence(cls, v):
        return round(v, 2)


class LLMAnalysisOutput(BaseModel):
    """Structured output from LLM - used by LangChain output parser"""
    impacted_currencies: List[CurrencyImpact] = Field(
        default_factory=list,
        description="List of impacted currencies with confidence >= 0.5"
    )

    @validator('impacted_currencies')
    def sort_by_confidence(cls, v):
        return sorted(v, key=lambda x: x.confidence, reverse=True)


class Headline(BaseModel):
    """Incoming headline from feed"""
    text: str
    source: str = "unknown"
    timestamp: datetime = Field(default_factory=datetime.now)
    metadata: dict = Field(default_factory=dict)


class ImpactAnalysisResult(BaseModel):
    """Complete analysis result"""
    headline: str
    timestamp: datetime
    impacted_entities: List[CurrencyImpact]
    processing_time_ms: float
    model_used: str
    error: Optional[str] = None
