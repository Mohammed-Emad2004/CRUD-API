from datetime import datetime
from enum import Enum
from typing import Literal, Optional
from pydantic import AnyHttpUrl, BaseModel, Field, ValidationError


class Category(str, Enum):
    fiction = "fiction"
    nonfiction = "nonfiction"
    poetry = "poetry"
    children = "children"
    mystery = "mystery"
    romance = "romance"
    other = "other"


class EnrichInput(BaseModel):
    title: str = Field(min_length=1)
    product_url: AnyHttpUrl
    price_gbp: float
    availability: int = Field(ge=0)
    rating: int = Field(ge=1, le=5)
    description: Optional[str] = None
    source_page: AnyHttpUrl
    fetched_at: datetime


class QualityFlag(str, Enum):
    missing_description = "missing_description"
    low_rating = "low_rating"
    low_availability = "low_availability"
    empty_quality_issue = "empty_quality_issue"


class EnrichOutput(BaseModel):
    category: Category
    summary: str = Field(min_length=1)
    quality_flags: list[QualityFlag] = Field(default_factory=list)

    class Config:
        use_enum_values = True


def validate_enrich_input(data: dict) -> EnrichInput:
    try:
        return EnrichInput(**data)
    except ValidationError as exc:
        errors = []
        for error in exc.errors():
            field = ".".join(str(part) for part in error["loc"])
            msg = error["msg"]
            errors.append({"field": field, "message": msg})
        raise ValueError(errors)


def validate_enrich_output(data: dict) -> EnrichOutput:
    try:
        return EnrichOutput(**data)
    except ValidationError as exc:
        errors = []
        for error in exc.errors():
            field = ".".join(str(part) for part in error["loc"])
            msg = error["msg"]
            errors.append({"field": field, "message": msg})
        raise ValueError(errors)