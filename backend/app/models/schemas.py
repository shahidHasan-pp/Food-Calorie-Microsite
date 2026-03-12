import logging
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class AnalyzeFoodResponse(BaseModel):
    success: bool
    food_name: str | None = None
    calories: int | None = None
    protein: float | None = None
    carbs: float | None = None
    fat: float | None = None
    sugar: float | None = None
    confidence_score: int | None = None
    error: str | None = None
    message: str | None = None


class ErrorResponse(BaseModel):
    success: bool = False
    error: str
    message: str
