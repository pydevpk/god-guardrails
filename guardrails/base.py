from typing import Dict, Any

class Guardrail:
    name = "base"

    async def check(self, context: Dict[str, Any]) -> Dict[str, Any]:
        return context