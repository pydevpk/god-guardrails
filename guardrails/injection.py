from .base import Guardrail

class InjectionGuardrail(Guardrail):
    name = "prompt_injection"

    async def check(self, context):
        text = context["query"].lower()

        if "ignore previous instructions" in text:
            context["blocked"] = True
            context["violations"].append("Prompt injection detected")

        return context