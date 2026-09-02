from pydantic import BaseModel
from typing import Optional, Dict, Any

class GuardrailRequest(BaseModel):
    app_id: str
    query: str
    metadata: Optional[Dict[str, Any]] = {}
    stream: Optional[bool] = False