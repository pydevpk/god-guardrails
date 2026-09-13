import pytest
from pydantic import ValidationError

from god_guardrails.schemas.request import GuardrailRequest
from god_guardrails.schemas.response import GuardrailDecision, GuardrailResponse


def test_request_requires_app_id_and_query():
    with pytest.raises(ValidationError):
        GuardrailRequest(query="hi")
    with pytest.raises(ValidationError):
        GuardrailRequest(app_id="app")


def test_request_defaults():
    req = GuardrailRequest(app_id="app", query="hi")
    assert req.system_prompt is None
    assert req.metadata == {}
    assert req.stream is False


def test_request_mutable_default_metadata_is_not_shared_between_instances():
    req1 = GuardrailRequest(app_id="app", query="hi")
    req2 = GuardrailRequest(app_id="app", query="hi")
    req1.metadata["leaked"] = True
    assert "leaked" not in req2.metadata


def test_request_accepts_explicit_system_prompt_and_metadata():
    req = GuardrailRequest(app_id="app", query="hi", system_prompt="sys",
                            metadata={"k": "v"}, stream=True)
    assert req.system_prompt == "sys"
    assert req.metadata == {"k": "v"}
    assert req.stream is True


def test_decision_accepts_allow_and_block():
    assert GuardrailDecision(action="allow").reasons == []
    assert GuardrailDecision(action="block", reasons=["x"]).reasons == ["x"]


def test_decision_rejects_invalid_action_value():
    with pytest.raises(ValidationError):
        GuardrailDecision(action="mask")
    with pytest.raises(ValidationError):
        GuardrailDecision(action="modify")
    with pytest.raises(ValidationError):
        GuardrailDecision(action="typo")


def test_response_wraps_output_and_decision():
    resp = GuardrailResponse(output="hi", decision=GuardrailDecision(action="allow"))
    assert resp.output == "hi"
    assert resp.decision.action == "allow"
