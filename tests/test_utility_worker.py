from god_guardrails.guardrails.base import UtilityWorker


# --- load_policies / load_global_policies / load_application_policies -------

async def test_load_policies_returns_dict_from_context():
    context = {"policies": {"global_policies": {"a": 1}}}
    assert await UtilityWorker.load_policies(context=context) == {"global_policies": {"a": 1}}


async def test_load_policies_defaults_to_empty_dict_when_missing():
    assert await UtilityWorker.load_policies(context={}) == {}


async def test_load_global_policies_returns_global_section():
    context = {"policies": {"global_policies": {"pii_masking": True}}}
    assert await UtilityWorker.load_global_policies(context=context) == {"pii_masking": True}


async def test_load_global_policies_defaults_to_empty_dict():
    assert await UtilityWorker.load_global_policies(context={"policies": {}}) == {}


async def test_load_application_policies_returns_matching_app_entry():
    context = {
        "app_id": "finance_bot",
        "policies": {"application_policies": {"finance_bot": {"pii_masking": False}}},
    }
    assert await UtilityWorker.load_application_policies(context=context) == {"pii_masking": False}


async def test_load_application_policies_returns_none_when_app_not_listed():
    context = {
        "app_id": "unknown_app",
        "policies": {"application_policies": {"finance_bot": {"pii_masking": False}}},
    }
    assert await UtilityWorker.load_application_policies(context=context) is None


async def test_load_application_policies_returns_none_when_app_id_missing():
    context = {"policies": {"application_policies": {"finance_bot": {}}}}
    assert await UtilityWorker.load_application_policies(context=context) is None


# --- load_pattern -------------------------------------------------------

async def test_load_pattern_formats_well_formed_entries():
    patterns = {"phone": ["[Phone]", r"\b\d{10}\b"], "email": ["[Email]", r"[a-z]+@[a-z]+"]}
    result = await UtilityWorker.load_pattern(patterns)
    assert result == [
        {"label": "[Phone]", "value": r"\b\d{10}\b"},
        {"label": "[Email]", "value": r"[a-z]+@[a-z]+"},
    ]


async def test_load_pattern_returns_empty_list_for_empty_input():
    assert await UtilityWorker.load_pattern({}) == []


async def test_load_pattern_skips_entry_with_too_few_elements():
    result = await UtilityWorker.load_pattern({"phone": ["[Phone]"]})
    assert result == []


async def test_load_pattern_skips_entry_that_is_not_a_list():
    result = await UtilityWorker.load_pattern({"phone": "[Phone]"})
    assert result == []


async def test_load_pattern_keeps_valid_entries_alongside_malformed_ones():
    patterns = {"phone": ["[Phone]"], "email": ["[Email]", r"[a-z]+@[a-z]+"]}
    result = await UtilityWorker.load_pattern(patterns)
    assert result == [{"label": "[Email]", "value": r"[a-z]+@[a-z]+"}]


async def test_load_pattern_without_context_does_not_crash_on_malformed_entry():
    # context is optional - calling load_pattern directly (no violations list available) must not raise.
    result = await UtilityWorker.load_pattern({"phone": ["[Phone]"]}, context=None)
    assert result == []


async def test_load_pattern_records_violation_for_malformed_entry_when_context_given():
    context = {"violations": []}
    await UtilityWorker.load_pattern({"phone": ["[Phone]"]}, context=context)
    assert context["violations"] == ["Invalid PII pattern skipped: phone"]


async def test_load_pattern_creates_violations_list_if_absent_from_context():
    context = {}
    await UtilityWorker.load_pattern({"phone": ["[Phone]"]}, context=context)
    assert context["violations"] == ["Invalid PII pattern skipped: phone"]


# --- check_masking_required -----------------------------------------------

async def test_masking_disabled_globally_and_no_app_override():
    context = {"app_id": "x", "policies": {"global_policies": {"pii_masking": False},
                                            "application_policies": {}}}
    is_pii, patterns = await UtilityWorker.check_masking_required(context=context)
    assert is_pii is False
    assert patterns == []


async def test_masking_enabled_globally_app_not_listed_inherits_global():
    context = {
        "app_id": "unlisted_app",
        "policies": {
            "global_policies": {"pii_masking": True, "patterns": {"phone": ["[Phone]", r"\d{10}"]}},
            "application_policies": {},
        },
    }
    is_pii, patterns = await UtilityWorker.check_masking_required(context=context)
    assert is_pii is True
    assert patterns == [{"label": "[Phone]", "value": r"\d{10}"}]


async def test_masking_enabled_globally_app_listed_but_silent_on_pii_masking_inherits_global():
    # Regression test: an app entry existing without mentioning pii_masking must NOT be
    # treated as an implicit disable.
    context = {
        "app_id": "some_app",
        "policies": {
            "global_policies": {"pii_masking": True, "patterns": {"phone": ["[Phone]", r"\d{10}"]}},
            "application_policies": {"some_app": {"block_topics": ["x"]}},
        },
    }
    is_pii, patterns = await UtilityWorker.check_masking_required(context=context)
    assert is_pii is True
    assert patterns == [{"label": "[Phone]", "value": r"\d{10}"}]


async def test_masking_app_explicitly_disables_overriding_global_true():
    context = {
        "app_id": "finance_bot",
        "policies": {
            "global_policies": {"pii_masking": True, "patterns": {"phone": ["[Phone]", r"\d{10}"]}},
            "application_policies": {"finance_bot": {"pii_masking": False}},
        },
    }
    is_pii, patterns = await UtilityWorker.check_masking_required(context=context)
    assert is_pii is False
    assert patterns == []


async def test_masking_app_explicitly_enables_with_own_patterns_replaces_global():
    context = {
        "app_id": "app1",
        "policies": {
            "global_policies": {"pii_masking": True, "patterns": {"phone": ["[Phone]", r"\d{10}"]}},
            "application_policies": {"app1": {"pii_masking": True, "patterns": {"custom": ["[X]", r"XX\d+"]}}},
        },
    }
    is_pii, patterns = await UtilityWorker.check_masking_required(context=context)
    assert is_pii is True
    assert patterns == [{"label": "[X]", "value": r"XX\d+"}]


async def test_masking_app_explicitly_enables_without_patterns_falls_back_to_global():
    context = {
        "app_id": "app1",
        "policies": {
            "global_policies": {"pii_masking": True, "patterns": {"phone": ["[Phone]", r"\d{10}"]}},
            "application_policies": {"app1": {"pii_masking": True}},
        },
    }
    is_pii, patterns = await UtilityWorker.check_masking_required(context=context)
    assert is_pii is True
    assert patterns == [{"label": "[Phone]", "value": r"\d{10}"}]


async def test_masking_global_disabled_app_explicitly_enables_with_no_patterns_anywhere():
    # Enabling at app level with neither app nor global patterns defined leaves an empty
    # pattern list - masking is "on" but has nothing to apply.
    context = {
        "app_id": "app1",
        "policies": {
            "global_policies": {"pii_masking": False},
            "application_policies": {"app1": {"pii_masking": True}},
        },
    }
    is_pii, patterns = await UtilityWorker.check_masking_required(context=context)
    assert is_pii is True
    assert patterns == []


async def test_masking_app_not_in_applications_mapping_at_all_inherits_global():
    context = {
        "app_id": "totally_absent",
        "policies": {
            "global_policies": {"pii_masking": True, "patterns": {"phone": ["[Phone]", r"\d{10}"]}},
            "application_policies": {"some_other_app": {"pii_masking": False}},
        },
    }
    is_pii, patterns = await UtilityWorker.check_masking_required(context=context)
    assert is_pii is True
    assert patterns == [{"label": "[Phone]", "value": r"\d{10}"}]


async def test_masking_malformed_global_pattern_records_violation_via_context():
    context = {
        "app_id": "x",
        "violations": [],
        "policies": {
            "global_policies": {"pii_masking": True, "patterns": {"phone": ["[Phone]"]}},
            "application_policies": {},
        },
    }
    is_pii, patterns = await UtilityWorker.check_masking_required(context=context)
    assert is_pii is True
    assert patterns == []
    assert context["violations"] == ["Invalid PII pattern skipped: phone"]


# --- check_injection_required ----------------------------------------------

async def test_injection_global_true_app_silent_inherits_enabled():
    context = {"app_id": "a1", "policies": {"global_policies": {"prompt_injection": True},
                                             "application_policies": {"a1": {}}}}
    assert await UtilityWorker.check_injection_required(context=context) is True


async def test_injection_global_true_app_explicitly_disables():
    context = {"app_id": "a1", "policies": {"global_policies": {"prompt_injection": True},
                                             "application_policies": {"a1": {"prompt_injection": False}}}}
    assert await UtilityWorker.check_injection_required(context=context) is False


async def test_injection_global_false_app_explicitly_enables():
    context = {"app_id": "a1", "policies": {"global_policies": {"prompt_injection": False},
                                             "application_policies": {"a1": {"prompt_injection": True}}}}
    assert await UtilityWorker.check_injection_required(context=context) is True


async def test_injection_global_false_app_silent_stays_disabled():
    context = {"app_id": "a1", "policies": {"global_policies": {"prompt_injection": False},
                                             "application_policies": {"a1": {}}}}
    assert await UtilityWorker.check_injection_required(context=context) is False


async def test_injection_defaults_to_false_when_policy_key_absent_entirely():
    context = {"app_id": "a1", "policies": {"global_policies": {}, "application_policies": {}}}
    assert await UtilityWorker.check_injection_required(context=context) is False
