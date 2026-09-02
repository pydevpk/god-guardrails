# god-guardrails

A small, policy-driven guardrails middleware for LLM requests. It sits in front of a
model call, runs a request through a chain of checks (PII masking, prompt-injection /
blocked-topic detection, ...), and returns either the (possibly modified) query or a
block decision — all driven by a single `policies.yaml` file instead of hardcoded logic.

## How it works

```
GuardrailRequest -> GuardrailPipeline -> [Guardrail, Guardrail, ...] -> GuardrailResponse
```

1. A request (`app_id` + `query`) comes in.
2. `PolicyLoader` reads `policies.yaml` and returns the global policies plus the full
   set of per-application policies.
3. A `context` dict is built (`query`, `app_id`, `violations`, `blocked`, `policies`)
   and passed through a `GuardrailPipeline` — an ordered list of guardrails **you
   choose when you build the pipeline**. There's nothing wired in globally: pick
   whichever guardrails an app needs, in whatever order makes sense (a guardrail's
   own policy, e.g. `pii_masking`, decides whether it actually does anything for
   a given request — being in the list doesn't force it to run).
4. Each guardrail's `check(context)` inspects/mutates the context and can set
   `context["blocked"] = True`, which short-circuits the rest of the pipeline.
5. The result is wrapped into a `GuardrailResponse` with an `action` (`allow` or
   `block`) and the list of `reasons`/violations.

## Project layout

| Path | Purpose |
|---|---|
| [schemas/request.py](schemas/request.py) | `GuardrailRequest` — input model (`app_id`, `query`, `metadata`, `stream`) |
| [schemas/response.py](schemas/response.py) | `GuardrailResponse` / `GuardrailDecision` — output model |
| [policies.yaml](policies.yaml) | Global + per-application policy config |
| [policies/loader.py](policies/loader.py) | `PolicyLoader` — reads the YAML, resolves policies for a given `app_id` |
| [pipeline/engine.py](pipeline/engine.py) | `GuardrailPipeline` — runs a list of guardrails in order, stops on `blocked` |
| [guardrails/base.py](guardrails/base.py) | `Guardrail` base class + `UtilityWorker` (policy resolution helpers) |
| [guardrails/pii.py](guardrails/pii.py) | `PIIGuardrail` — regex-based PII masking |
| [guardrails/injection.py](guardrails/injection.py) | `InjectionGuardrail` — blocked-topic detection |
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
    block_topics:
      - investment_advice

  support_bot:
    pii_masking: true
    block_topics:
      - refunds
```

The document has two parts:

- **`global`** — defaults that apply to every application.
- **`applications.<app_id>`** — per-application overrides.

Every guardrail-relevant setting (`pii_masking`, `prompt_injection`, `patterns`,
`block_topics`, ...) follows the same **global → application** resolution rule:

- If an application doesn't mention a key at all, it **inherits the global value**.
- If an application explicitly sets that key, its value **overrides the global one**
  for that app (booleans and lists are replaced outright, not merged).

This resolution is implemented once in `UtilityWorker` and reused by every guardrail:

- `check_masking_required(context)` → `(is_enabled, patterns)` for `pii_masking`
- `check_injection_required(context)` → `bool` for `prompt_injection`
- `check_block_topics(context)` → `list[str]` for `block_topics`

Because it's centralized, adding a new policy-driven guardrail just means adding a
similar `check_*` resolver and calling it from the guardrail's `check()`.

`patterns` (used by `PIIGuardrail`) is a mapping of `label -> [replacement, regex]`,
e.g. `phone: ["[Phone]", '\b\d{10}\b']` masks any 10-digit number with `[Phone]`.
An application can define its own `patterns` to fully replace the global ones when
it also sets `pii_masking: true`.

`block_topics` (used by `InjectionGuardrail`) is a simple list of topic strings.
The guardrail checks (case-insensitively, underscores treated as spaces) whether
any listed topic appears in the query text, and blocks the request if so.

## Usage

Install dependencies:

```bash
pip install -r requirements.txt
```

Run the example in [test.py](test.py):

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

async def generate(req: GuardrailRequest):
    policies = policy_loader.get_policies(req.app_id)

    context = {
        "query": req.query,
        "app_id": req.app_id,
        "violations": [],
        "blocked": False,
        "policies": policies,
    }

    # any subset of guardrails, in any order
    pipeline = GuardrailPipeline([PIIGuardrail(), InjectionGuardrail()])
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
