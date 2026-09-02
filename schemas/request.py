from pydantic import BaseModel
from typing import Optional, Dict, Any

class GuardrailRequest(BaseModel):
    app_id: str
    query: str
    system_prompt: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = {}
    stream: Optional[bool] = False