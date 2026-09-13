import pytest


@pytest.fixture
def make_context():
    """
    Builds a pipeline context dict without needing a real PolicyLoader/yaml file -
    tests pass global_policies/application_policies directly to exercise resolution.
    """
    def _make(query="hello", app_id="test_app", system_prompt=None,
              global_policies=None, application_policies=None, **extra):
        context = {
            "query": query,
            "app_id": app_id,
            "system_prompt": system_prompt,
            "violations": [],
            "blocked": False,
            "policies": {
                "global_policies": global_policies if global_policies is not None else {},
                "application_policies": application_policies if application_policies is not None else {},
            },
        }
        context.update(extra)
        return context
    return _make


@pytest.fixture
def llm_safe():
    async def _llm(prompt):
        return "SAFE"
    return _llm


@pytest.fixture
def llm_injection():
    async def _llm(prompt):
        return "INJECTION"
    return _llm


@pytest.fixture
def llm_raising():
    async def _llm(prompt):
        raise TimeoutError("provider timed out")
    return _llm


@pytest.fixture
def llm_garbage():
    async def _llm(prompt):
        return "uh, what?"
    return _llm


@pytest.fixture
def recording_llm():
    """Returns (llm, calls) - calls collects every prompt the guardrail sent, and always answers SAFE."""
    calls = []

    async def _llm(prompt):
        calls.append(prompt)
        return "SAFE"

    return _llm, calls
