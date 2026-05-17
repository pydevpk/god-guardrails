import re
from .base import Guardrail

class PIIGuardrail(Guardrail):
    name = "pii"

    async def check(self, context):
        text = context["query"]

        # simple example (replace with Presidio later)
        masked = re.sub(r"\b\d{10}\b", "[PHONE]", text)

        if masked != text:
            context["query"] = masked
            context["violations"].append("PII masked")

        return context