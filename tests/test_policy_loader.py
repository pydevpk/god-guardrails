import pytest

from god_guardrails.policies.loader import PolicyLoader

SAMPLE_YAML = """
global:
  pii_masking: true
  prompt_injection: true
  patterns:
    phone:
      - "[Phone]"
      - '\\b\\d{10}\\b'

applications:
  finance_bot:
    pii_masking: false
  support_bot:
    pii_masking: true
"""


@pytest.fixture
def sample_policy_file(tmp_path):
    path = tmp_path / "policies.yaml"
    path.write_text(SAMPLE_YAML)
    return str(path)


def test_loader_parses_global_and_application_sections(sample_policy_file):
    loader = PolicyLoader(sample_policy_file)
    result = loader.get_policies("support_bot")

    assert result["global_policies"]["pii_masking"] is True
    assert result["global_policies"]["prompt_injection"] is True
    assert result["application_policies"]["finance_bot"]["pii_masking"] is False
    assert result["application_policies"]["support_bot"]["pii_masking"] is True


def test_loader_returns_full_applications_mapping_regardless_of_app_id(sample_policy_file):
    # get_policies scopes nothing itself - it hands back every application's policy
    # and leaves the per-app_id lookup to UtilityWorker downstream.
    loader = PolicyLoader(sample_policy_file)
    for app_id in ("finance_bot", "support_bot", "some_unlisted_app"):
        result = loader.get_policies(app_id)
        assert set(result["application_policies"].keys()) == {"finance_bot", "support_bot"}


def test_loader_handles_missing_global_section(tmp_path):
    path = tmp_path / "policies.yaml"
    path.write_text("applications:\n  finance_bot:\n    pii_masking: false\n")
    loader = PolicyLoader(str(path))
    result = loader.get_policies("finance_bot")
    assert result["global_policies"] == {}


def test_loader_handles_missing_applications_section(tmp_path):
    path = tmp_path / "policies.yaml"
    path.write_text("global:\n  pii_masking: true\n")
    loader = PolicyLoader(str(path))
    result = loader.get_policies("anything")
    assert result["application_policies"] == {}


def test_loader_raises_for_missing_file():
    with pytest.raises(FileNotFoundError):
        PolicyLoader("/nonexistent/path/policies.yaml")


def test_real_repo_policies_yaml_has_expected_shape():
    """Guards against accidental regressions in the shipped example policies.yaml."""
    loader = PolicyLoader("policies.yaml")
    result = loader.get_policies("support_bot")
    assert result["global_policies"]["pii_masking"] is True
    assert result["global_policies"]["prompt_injection"] is True
    assert "patterns" in result["global_policies"]
    assert result["application_policies"]["finance_bot"]["pii_masking"] is False
    assert result["application_policies"]["support_bot"]["pii_masking"] is True
