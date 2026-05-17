from pydantic import BaseModel
from typing import Optional, Dict, Any

class GuardrailRequest(BaseModel):
    app_id: str
    user_id: Optional[str]
    query: str
    metadata: Optional[Dict[str, Any]] = {}
    stream: Optional[bool] = False