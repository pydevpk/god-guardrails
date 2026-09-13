from god_guardrails.guardrails.base import Guardrail
from god_guardrails.pipeline.engine import GuardrailPipeline


class RecordingGuardrail(Guardrail):
    """Appends its name to context['order'] every time it runs."""

    def __init__(self, name):
        self.name = name

    async def check(self, context):
        context.setdefault("order", []).append(self.name)
        return context


class BlockingGuardrail(Guardrail):
    def __init__(self, name):
        self.name = name

    async def check(self, context):
        context.setdefault("order", []).append(self.name)
        context["blocked"] = True
        return context


async def test_empty_pipeline_returns_context_unchanged():
    context = {"query": "hi", "blocked": False}
    result = await GuardrailPipeline([]).run(context)
    assert result == context


async def test_guardrails_run_in_the_given_order():
    context = {"query": "hi", "blocked": False}
    pipeline = GuardrailPipeline([RecordingGuardrail("a"), RecordingGuardrail("b"), RecordingGuardrail("c")])
    result = await pipeline.run(context)
    assert result["order"] == ["a", "b", "c"]


async def test_reversed_order_also_respected():
    context = {"query": "hi", "blocked": False}
    pipeline = GuardrailPipeline([RecordingGuardrail("c"), RecordingGuardrail("b"), RecordingGuardrail("a")])
    result = await pipeline.run(context)
    assert result["order"] == ["c", "b", "a"]


async def test_pipeline_short_circuits_after_a_guardrail_blocks():
    context = {"query": "hi", "blocked": False}
    pipeline = GuardrailPipeline([
        RecordingGuardrail("first"),
        BlockingGuardrail("second"),
        RecordingGuardrail("third"),
    ])
    result = await pipeline.run(context)
    assert result["order"] == ["first", "second"]
    assert result["blocked"] is True


async def test_single_guardrail_pipeline_runs_fine():
    context = {"query": "hi", "blocked": False}
    result = await GuardrailPipeline([RecordingGuardrail("solo")]).run(context)
    assert result["order"] == ["solo"]


async def test_base_guardrail_check_is_a_no_op():
    context = {"query": "hi", "blocked": False}
    result = await Guardrail().check(context)
    assert result is context
