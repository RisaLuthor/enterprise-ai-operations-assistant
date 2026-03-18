from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


class SQLGenerateRequest(BaseModel):
    user_text: str = Field(..., min_length=3, max_length=2000)
    top_n: int = Field(default=100, ge=1, le=500)
    schema_name: Optional[str] = Field(default=None, min_length=1, max_length=100)

    @field_validator("user_text")
    @classmethod
    def validate_user_text(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("user_text must not be blank.")
        return cleaned


class SQLGenerateResponse(BaseModel):
    dialect: str
    query: str
    assumptions: List[str]
    safety_notes: List[str]
    suggested_next_inputs: List[str]
    plan: str
    risk_level: str