class GuardrailPipeline:
    def __init__(self, guardrails):
        self.guardrails = guardrails

    async def run(self, context):
        for guardrail in self.guardrails:
            context = await guardrail.check(context)

            if context.get("blocked"):
                return context

        return context