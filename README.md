# god-guardrails

A small, policy-driven guardrails middleware for LLM requests. It sits in front of a
model call, runs a request through a chain of checks (PII masking, prompt-injection
detection), and returns either the (possibly modified) query or a block decision —
driven by a single `policies.yaml` file instead of hardcoded logic. It does exactly
two things: **PII masking** and **prompt-injection detection**.

## How it works

```
GuardrailRequest -> GuardrailPipeline -> [Guardrail, Guardrail, ...] -> GuardrailResponse
```

1. A request (`app_id`, `query`, optionally `system_prompt`) comes in.
2. `PolicyLoader` reads `policies.yaml` and returns the global policies plus the full
   set of per-application policies.
3. A `context` dict is built (`query`, `app_id`, `system_prompt`, `violations`,
   `blocked`, `policies`) and passed through a `GuardrailPipeline` — an ordered list
   of guardrails **you choose when you build the pipeline**. There's nothing wired
   in globally: pick whichever guardrails an app needs, in whatever order makes
   sense (a guardrail's own policy, e.g. `pii_masking`, decides whether it actually
   does anything for a given request — being in the list doesn't force it to run).
4. Each guardrail's `check(context)` inspects/mutates the context and can set
   `context["blocked"] = True`, which short-circuits the rest of the pipeline.
5. The result is wrapped into a `GuardrailResponse` with an `action` (`allow` or
   `block`) and the list of `reasons`/violations.

## Project layout

| Path | Purpose |
|---|---|
| [schemas/request.py](schemas/request.py) | `GuardrailRequest` — input model (`app_id`, `query`, `system_prompt`, `metadata`, `stream`) |
| [schemas/response.py](schemas/response.py) | `GuardrailResponse` / `GuardrailDecision` — output model |
| [policies.yaml](policies.yaml) | Global + per-application policy config |
| [policies/loader.py](policies/loader.py) | `PolicyLoader` — reads the YAML, resolves policies for a given `app_id` |
| [pipeline/engine.py](pipeline/engine.py) | `GuardrailPipeline` — runs a list of guardrails in order, stops on `blocked` |
| [guardrails/base.py](guardrails/base.py) | `Guardrail` base class + `UtilityWorker` (policy resolution helpers) |
| [guardrails/pii.py](guardrails/pii.py) | `PIIGuardrail` — regex-based PII masking |
| [guardrails/injection.py](guardrails/injection.py) | `InjectionGuardrail` — LLM-based system-prompt-bypass detection |
| [test.py](test.py) | Example entry point showing how to assemble and run a pipeline |

## Policy model (`policies.yaml`)

```yaml
global:
  pii_masking: true
  prompt_injection: true
  patterns:
    phone:
      - "[Phone]"
      - '\b\d{10}\b'
    email:
      - '[Email]'
      - '[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'

applications:
  finance_bot:
    pii_masking: false

  support_bot:
    pii_masking: true
```

The document has two parts:

- **`global`** — defaults that apply to every application.
- **`applications.<app_id>`** — per-application overrides.

Both `pii_masking` and `prompt_injection` follow the same **global → application**
resolution rule:

- If an application doesn't mention the key at all, it **inherits the global value**.
- If an application explicitly sets the key, its value **overrides the global one**
  for that app (booleans and lists are replaced outright, not merged).

This resolution is implemented once in `UtilityWorker` and reused by every guardrail:

- `check_masking_required(context)` → `(is_enabled, patterns)` for `pii_masking`
- `check_injection_required(context)` → `bool` for `prompt_injection`

Because it's centralized, adding a new policy-driven guardrail just means adding a
similar `check_*` resolver and calling it from the guardrail's `check()`.

`patterns` (used by `PIIGuardrail`) is a mapping of `label -> [replacement, regex]`,
e.g. `phone: ["[Phone]", '\b\d{10}\b']` masks any 10-digit number with `[Phone]`.
An application can define its own `patterns` to fully replace the global ones when
it also sets `pii_masking: true`. A malformed pattern entry (bad regex, or missing
its replacement/regex pair) is skipped rather than crashing the request — every
other valid pattern still applies, and a violation records which one was skipped.

`prompt_injection` only controls whether the check runs; **what counts as an
attack is not configured in policy at all** — see below.

## Prompt-injection detection

`InjectionGuardrail` isn't a keyword or topic filter. Its only job is deciding
whether `query` attempts to override, ignore, bypass, or extract the caller's
`system_prompt` (the instructions that define your assistant's behavior — sent
in the request alongside the query). Anything else — which topics your assistant
should or shouldn't discuss, tone, capabilities — belongs in your own
`system_prompt`, not in `policies.yaml`. The guardrail doesn't need to know it.

The check itself is delegated to an LLM you provide, since this project doesn't
own a model client for any provider:

```python
class InjectionGuardrail(Guardrail):
    def __init__(self, llm=None):
        self.llm = llm
```

`llm` must be an `async def llm(prompt: str) -> str` callable — given a single
prompt string, return the model's raw text reply. `InjectionGuardrail` builds the
full detection prompt itself (embedding your `system_prompt` and the `query`) and
parses the reply, so the adapter can wrap any provider:

```python
async def llm(prompt: str) -> str:
    response = await my_provider_client.complete(prompt)
    return response.text

InjectionGuardrail(llm=llm)
```

Behavior, since this is a security control and an unverifiable check is treated
as unsafe by default (fail closed):

- `prompt_injection` disabled for the app → skipped entirely, no `llm` needed.
- Enabled but no `llm` was configured on the guardrail → raises `RuntimeError`
  immediately (a setup bug to fix, not a per-request condition).
- Enabled but the request has no `system_prompt` → **blocked** (nothing to check
  the query against).
- The `llm` callable raises, or its reply isn't recognizably `SAFE`/`INJECTION`
  → **blocked** (can't verify safety).
- Reply parses as `INJECTION` → **blocked**. Parses as `SAFE` → allowed.

## Usage

Install dependencies:

```bash
pip install -r requirements.txt
```

Run the example in [test.py](test.py) (it wires in a small mock `llm` callable
purely to keep the example runnable without a real provider — swap it out):

```bash
python test.py
```

To build your own request flow, compose a pipeline from whichever guardrails you
need, in whatever order you want:

```python
from schemas.request import GuardrailRequest
from schemas.response import GuardrailResponse, GuardrailDecision
from policies.loader import PolicyLoader
from pipeline.engine import GuardrailPipeline
from guardrails.pii import PIIGuardrail
from guardrails.injection import InjectionGuardrail

policy_loader = PolicyLoader("policies.yaml")

async def llm(prompt: str) -> str:
    response = await my_provider_client.complete(prompt)
    return response.text

async def generate(req: GuardrailRequest):
    policies = policy_loader.get_policies(req.app_id)

    context = {
        "query": req.query,
        "app_id": req.app_id,
        "system_prompt": req.system_prompt,
        "violations": [],
        "blocked": False,
        "policies": policies,
    }

    # any subset of guardrails, in any order
    pipeline = GuardrailPipeline([PIIGuardrail(), InjectionGuardrail(llm=llm)])
    context = await pipeline.run(context)

    if context.get("blocked"):
        return GuardrailResponse(
            output="Request blocked due to policy violation",
            decision=GuardrailDecision(action="block", reasons=context["violations"]),
        )

    return GuardrailResponse(
        output=context["query"],
        decision=GuardrailDecision(action="allow"),
    )
```

## Adding a new guardrail

1. Subclass `Guardrail` (from [guardrails/base.py](guardrails/base.py)) and implement
   `async def check(self, context: dict) -> dict`.
2. If it needs policy-driven configuration, add a `check_*` resolver to
   `UtilityWorker` following the global→application override pattern described
   above, and add the corresponding key(s) to `policies.yaml`.
3. Add an instance of your guardrail to the pipeline list wherever it's built
   (e.g. in your own version of `generate()`).
