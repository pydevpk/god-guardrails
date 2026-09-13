from pydantic import BaseModel
from typing import List, Literal

class GuardrailDecision(BaseModel):
    action: Literal["allow", "block"]
    reasons: List[str] = []

class GuardrailResponse(BaseModel):
    output: str
    decision: GuardrailDecision