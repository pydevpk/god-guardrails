import asyncio

from schemas.request import GuardrailRequest
from schemas.response import GuardrailResponse, GuardrailDecision

from policies.loader import PolicyLoader
from pipeline.engine import GuardrailPipeline

from guardrails.pii import PIIGuardrail
from guardrails.injection import InjectionGuardrail



policy_loader = PolicyLoader("policies.yaml")


async def mock_llm(prompt: str) -> str:
    """
    Stand-in for a real provider call. InjectionGuardrail only requires an
    `async def llm(prompt: str) -> str` callable - swap this for e.g. an
    Anthropic/OpenAI client call and return the model's raw text reply.
    """
    model_res = "SAFE"
    return model_res


async def generate(req: GuardrailRequest):

    policies = policy_loader.get_policies(req.app_id)

    context = {
        "query": req.query,
        "app_id": req.app_id,
        "system_prompt": req.system_prompt,
        "violations": [],
        "blocked": False,
        "policies": policies
    }

    pipeline = GuardrailPipeline([
        PIIGuardrail(),
        InjectionGuardrail(llm=mock_llm),
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
        output=context['query'],
        decision=GuardrailDecision(
            action="allow"
        )
    )


async def main():
    req = GuardrailRequest(
        app_id="support_bot",
        system_prompt="You are a support assistant. Only help with refund questions. ",
        query="Call me at 9876543210 or email test@example.com",
    )

    result = await generate(req=req)
    print(result)


if __name__ == "__main__":
    asyncio.run(main())