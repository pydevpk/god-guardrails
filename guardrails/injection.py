from .base import Guardrail, UtilityWorker

class InjectionGuardrail(Guardrail):
    name = "prompt_injection"

    async def check(self, context):
        is_required = await UtilityWorker.check_injection_required(context=context)

        if is_required:
            text = context["query"].lower()
            block_topics = await UtilityWorker.check_block_topics(context=context)

            for topic in block_topics:
                topic_phrase = topic.replace("_", " ").lower()

                if topic_phrase in text:
                    context["blocked"] = True
                    context["violations"].append(f"Blocked topic detected: {topic}")

        return context