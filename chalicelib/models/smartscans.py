from pydantic import BaseModel, Field, PositiveFloat

__all__ = ["SmartScanResult"]


class SmartScanResult(BaseModel):
    merchant: str = Field(..., examples=["Amazon"])
    date: str = Field(..., examples=["2023-01-01"])
    amount: PositiveFloat = Field(..., examples=[100.0])
    currency: str = Field(..., examples=["USD"])
    category: str = Field(..., examples=["Office Supplies"])
    createdAt: str = Field(..., examples=["2023-01-01T12:00:00Z"])
    confidence: PositiveFloat = Field(..., examples=[0.95])
