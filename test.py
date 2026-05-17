import asyncio

from schemas.request import GuardrailRequest
from schemas.response import GuardrailResponse, GuardrailDecision

from policies.loader import PolicyLoader
from pipeline.engine import GuardrailPipeline
from guardrails.pii import PIIGuardrail
from guardrails.injection import InjectionGuardrail



policy_loader = PolicyLoader("policies.yaml")

async def generate(req: GuardrailRequest):

    policies = policy_loader.get_policies(req.app_id)

    context = {
        "query": req.query,
        "app_id": req.app_id,
        "violations": [],
        "blocked": False,
        "policies": policies
    }

    pipeline = GuardrailPipeline([
        PIIGuardrail(),
        InjectionGuardrail(),
    ])

    context = await pipeline.run(context)

    if context.get("blocked"):
        return GuardrailResponse(
            output="Request blocked due to policy violation",
            decision=GuardrailDecision(
                action="block",
                reasons=context["violations"]
            )
        )

    return GuardrailResponse(
        output="allow",
        decision=GuardrailDecision(
            action="allow"
        )
    )


async def main():
    req = GuardrailRequest(
        app_id="123",
        user_id="1",
        query="Hello",
    )

    result = await generate(req=req)
    print(result)


if __name__ == "__main__":
    asyncio.run(main())