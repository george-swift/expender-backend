from datetime import datetime

from pydantic import BaseModel, Field, PositiveFloat, field_validator

from chalicelib import constants

__all__ = ["Expense"]


class Receipt(BaseModel):
    name: str = Field(..., description="File name of the uploaded receipt")
    size: int = Field(..., description="File size in bytes of the uploaded receipt")
    url: str = Field(..., description="Cloudfront URL of the uploaded receipt")


class Expense(BaseModel):
    date: str = Field(
        ..., description="Date of incurring the expense in ISO 8601 format"
    )
    amount: PositiveFloat = Field(..., description="Amount of incurred expense")
    currency: str = Field(
        default="USD",
        description="Currency of incurred expense for multi-currency support in later versions",
    )
    category: str = Field(..., description="Category of incurred expense")
    merchant: str | None = Field(
        default=None,
        description="Name of merchant, outlet or business where expense was incurred",
    )
    description: str | None = Field(
        default=None, description="Brief notes on expense incurred", max_length=140
    )
    scanId: str | None = Field(
        default=None,
        description="ID of the smartscan result used to create this expense",
    )
    receipt: Receipt | None = Field(
        default=None,
        description="Details about the receipt uploaded for smart scanning",
    )

    @field_validator("date")
    def validate_date(cls, value):
        try:
            datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            raise ValueError(
                f"Invalid date '{value}'. Must be ISO 8601 format (e.g., 2025-04-09T14:30:00Z)"
            )
        return value

    @field_validator("category")
    def validate_category(cls, value):
        if value not in constants.CATEGORIES:
            raise ValueError(
                f"Invalid category. Must be one of: {', '.join(constants.CATEGORIES)}"
            )
        return value

    @field_validator("currency")
    def validate_currency(cls, value):
        if value not in constants.CURRENCY_PATTERNS:
            raise ValueError(
                f"Invalid currency. Must be one of: {', '.join(constants.CURRENCY_PATTERNS.keys())}"
            )
        return value
