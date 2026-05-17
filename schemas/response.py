from pydantic import BaseModel
from typing import List, Optional

class GuardrailDecision(BaseModel):
    action: str  # allow | block | mask | modify
    reasons: List[str] = []

class GuardrailResponse(BaseModel):
    output: str
    decision: GuardrailDecision