from god_guardrails.guardrails.pii import PIIGuardrail


async def test_masking_disabled_leaves_query_untouched(make_context):
    context = make_context(
        query="call 9876543210",
        global_policies={"pii_masking": False},
    )
    result = await PIIGuardrail().check(context)
    assert result["query"] == "call 9876543210"
    assert result["violations"] == []
    assert result["blocked"] is False


async def test_single_pattern_match_masks_and_records_violation(make_context):
    context = make_context(
        query="call 9876543210",
        global_policies={"pii_masking": True, "patterns": {"phone": ["[Phone]", r"\b\d{10}\b"]}},
    )
    result = await PIIGuardrail().check(context)
    assert result["query"] == "call [Phone]"
    assert result["violations"] == ["PII masked: [Phone]"]


async def test_multiple_patterns_all_match_and_all_recorded(make_context):
    context = make_context(
        query="call 9876543210 or email test@example.com",
        global_policies={
            "pii_masking": True,
            "patterns": {
                "phone": ["[Phone]", r"\b\d{10}\b"],
                "email": ["[Email]", r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"],
            },
        },
    )
    result = await PIIGuardrail().check(context)
    assert result["query"] == "call [Phone] or email [Email]"
    assert set(result["violations"]) == {"PII masked: [Phone]", "PII masked: [Email]"}


async def test_pattern_with_no_match_leaves_query_untouched(make_context):
    context = make_context(
        query="nothing sensitive here",
        global_policies={"pii_masking": True, "patterns": {"phone": ["[Phone]", r"\b\d{10}\b"]}},
    )
    result = await PIIGuardrail().check(context)
    assert result["query"] == "nothing sensitive here"
    assert result["violations"] == []


async def test_pii_guardrail_never_sets_blocked(make_context):
    context = make_context(
        query="call 9876543210",
        global_policies={"pii_masking": True, "patterns": {"phone": ["[Phone]", r"\b\d{10}\b"]}},
    )
    result = await PIIGuardrail().check(context)
    assert result["blocked"] is False


async def test_malformed_regex_is_skipped_but_valid_pattern_still_applies(make_context):
    context = make_context(
        query="call 9876543210 or email test@example.com",
        global_policies={
            "pii_masking": True,
            "patterns": {
                "phone": ["[Phone]", r"\b\d{10}("],  # unbalanced paren - invalid regex
                "email": ["[Email]", r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"],
            },
        },
    )
    result = await PIIGuardrail().check(context)
    assert result["query"] == "call 9876543210 or email [Email]"
    assert "Invalid PII pattern skipped: [Phone]" in result["violations"]
    assert "PII masked: [Email]" in result["violations"]


async def test_structurally_malformed_pattern_is_skipped_but_valid_pattern_still_applies(make_context):
    context = make_context(
        query="call 9876543210 or email test@example.com",
        global_policies={
            "pii_masking": True,
            "patterns": {
                "phone": ["[Phone]"],  # missing regex - malformed shape
                "email": ["[Email]", r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"],
            },
        },
    )
    result = await PIIGuardrail().check(context)
    assert result["query"] == "call 9876543210 or email [Email]"
    assert "Invalid PII pattern skipped: phone" in result["violations"]
    assert "PII masked: [Email]" in result["violations"]


async def test_all_patterns_malformed_does_not_crash_and_leaves_query_untouched(make_context):
    context = make_context(
        query="call 9876543210",
        global_policies={"pii_masking": True, "patterns": {"phone": ["[Phone]"]}},
    )
    result = await PIIGuardrail().check(context)
    assert result["query"] == "call 9876543210"
    assert result["violations"] == ["Invalid PII pattern skipped: phone"]


async def test_app_override_disables_masking_even_though_global_enables_it(make_context):
    context = make_context(
        query="call 9876543210",
        app_id="finance_bot",
        global_policies={"pii_masking": True, "patterns": {"phone": ["[Phone]", r"\b\d{10}\b"]}},
        application_policies={"finance_bot": {"pii_masking": False}},
    )
    result = await PIIGuardrail().check(context)
    assert result["query"] == "call 9876543210"
    assert result["violations"] == []


async def test_app_override_uses_its_own_patterns_instead_of_global(make_context):
    context = make_context(
        query="secret code AB1234",
        app_id="custom_app",
        global_policies={"pii_masking": True, "patterns": {"phone": ["[Phone]", r"\b\d{10}\b"]}},
        application_policies={"custom_app": {"pii_masking": True, "patterns": {"code": ["[Code]", r"[A-Z]{2}\d{4}"]}}},
    )
    result = await PIIGuardrail().check(context)
    assert result["query"] == "secret code [Code]"
    assert result["violations"] == ["PII masked: [Code]"]


async def test_app_listed_but_silent_on_pii_masking_still_inherits_and_masks(make_context):
    context = make_context(
        query="call 9876543210",
        app_id="support_bot",
        global_policies={"pii_masking": True, "patterns": {"phone": ["[Phone]", r"\b\d{10}\b"]}},
        application_policies={"support_bot": {"block_topics": ["refunds"]}},
    )
    result = await PIIGuardrail().check(context)
    assert result["query"] == "call [Phone]"
    assert result["violations"] == ["PII masked: [Phone]"]
