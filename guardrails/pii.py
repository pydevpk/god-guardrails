import re
from .base import Guardrail, UtilityWorker

class PIIGuardrail(Guardrail):
    name = "pii"

    async def check(self, context):
        text = context["query"]

        is_pii, patterns = await UtilityWorker.check_masking_required(
            context=context
        )

        if is_pii:
            for pattern in patterns:
                regex_pattern = pattern["value"]
                label = pattern["label"]

                try:
                    masked = re.sub(
                        regex_pattern,
                        label,
                        text
                    )
                except re.error:
                    context["violations"].append(f"Invalid PII pattern skipped: {label}")
                    continue

                if masked != text:
                    text = masked
                    context["violations"].append(f"PII masked: {label}")

            context["query"] = text

        return context