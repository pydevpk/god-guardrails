import asyncio

from openai import AsyncOpenAI

from god_guardrails.schemas.request import GuardrailRequest
from god_guardrails.schemas.response import GuardrailResponse, GuardrailDecision

from god_guardrails.policies.loader import PolicyLoader
from god_guardrails.pipeline.engine import GuardrailPipeline

from god_guardrails.guardrails.pii import PIIGuardrail
from god_guardrails.guardrails.injection import InjectionGuardrail



policy_loader = PolicyLoader("policies.yaml")
openai_client = AsyncOpenAI()  # reads OPENAI_API_KEY from the environment


async def openai_llm(prompt: str) -> str:
    """
    InjectionGuardrail only requires an `async def llm(prompt: str) -> str` callable -
    this adapter fulfills it using OpenAI's chat completions API.
    """
    response = await openai_client.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.choices[0].message.content


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
        InjectionGuardrail(llm=openai_llm),
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