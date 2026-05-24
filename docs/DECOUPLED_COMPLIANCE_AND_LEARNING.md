# Decoupled Compliance and Continuous Learning

Version: v4.0 -- Last audited: 2026-05-24

---

## The Problem with Hardcoded Compliance

The conventional approach to AI agent compliance encodes policy rules directly in the agent's system prompt:

```text
You are a routing agent.
If the user requests compute, provision it.
If deploying to a Spot Instance, include 'budget_tag: approved'.
Never expose salary data.
```

This creates three operational problems:

1. **Policy updates require code deployments.** Every time Legal, HR, or FinOps revises a rule, an engineer must edit the prompt, test it, and redeploy. This is impractical at scale across dozens of agents.
2. **Token overhead degrades model performance.** Encoding all enterprise policies (FinOps, HR, Legal, Security) into every agent's system prompt increases token count and reduces the model's available context for its primary task.
3. **Remediation is slow.** When a violation is detected in production, the standard workflow involves manual log review, ticket creation, developer assignment, prompt editing, and redeployment. The vulnerable agent remains unpatched during this window.

---

## Decoupled Compliance via Vertex AI Search

AeroCaliper separates compliance rules from the agent codebase by storing policy documents in two Vertex AI Search datastores:

- `finops-app`: Contains the Enterprise FinOps Routing Policy (Spot Instance requirements, budget tag enforcement, cluster allowlists).
- `hr-app`: Contains the Enterprise HR Privacy and PII Policy (salary data redaction, offer letter handling, contractor data restrictions).

When a violation is detected, AeroCaliper does not consult any hardcoded policy text. Instead, it queries the appropriate datastore using `discoveryengine_v1.SearchServiceClient` with an engine-level serving config to return extractive answer snippets -- the exact policy clause relevant to the detected violation.

The active datastore is selected at runtime based on `target_use_case` (`finops` maps to `VERTEX_ENGINE_ID_FINOPS`; `hr` maps to `VERTEX_ENGINE_ID_HR`). No code changes are required when switching domains.

**Practical consequence:** Policy owners can update a PDF or text file in GCP Cloud Storage and import it into the appropriate datastore. The next AeroCaliper run will fetch the updated clause automatically. No engineer involvement is required for routine policy updates.

**Failure behavior:** If the datastore returns zero extractive answer snippets (for example, during the 10 to 30 minute indexing window after a document import), the pipeline raises `RuntimeError`. It does not fall back to hardcoded policy text.

---

## The Golden Dataset and Empirical Backtesting

`golden_dataset.csv` contains labeled historical test cases covering both compliant and non-compliant agent behaviors across both domains. Each row includes a user prompt, the expected agent output schema, the compliance verdict, and a domain tag (`finops` or `hr`).

When AeroCaliper generates a candidate patch in Phase 3, it must demonstrate that the patched prompt:

1. Blocks the specific violation that triggered remediation.
2. Does not break existing compliant workflows.

Phase 4 satisfies this by filtering `golden_dataset.csv` to the active domain and running each case through a live Gemini inference call using the candidate prompt as the system instruction. Results are scored by `evaluate_finops_compliance()` or `evaluate_hr_compliance()` in `evaluators.py`.

Pass rate is computed over the filtered set only. A FinOps backtest never evaluates HR rows, and vice versa. This prevents cross-domain false failures from distorting the pass rate.

---

## Phase 4 Optimization Loop

A single backtesting attempt is insufficient to handle all edge cases reliably. AeroCaliper implements a loop of up to 3 attempts:

1. **Attempt 1:** The candidate prompt generated in Phase 3 is tested against the full filtered golden dataset.
2. **If failures occur:** The failure context (user prompt, expected behavior, actual Gemini output, evaluator verdict) is appended to a refinement prompt and submitted to Gemini. The resulting refined candidate replaces the current one.
3. **Attempt 2 and 3:** The refined candidate is re-tested. A 100% pass rate at any attempt exits the loop.
4. **After 3 failed attempts:** The pipeline fails closed. No partial patches are deployed.

This design allows the system to self-correct from initial prompt generation errors (for example, missing a specific edge case in the golden dataset) without manual intervention.

---

## Fail-Closed Architecture

AeroCaliper enforces a strict fail-closed policy at three points in the pipeline:

1. **Vertex AI Search (Phase 3):** If the datastore returns zero extractive answers, the pipeline halts with `RuntimeError`. Proceeding with incomplete policy context would produce an ungrounded diagnosis.
2. **Arize MCP and GraphQL Fallback (Phase 3):** If `get-spans` returns an empty response and the GraphQL fallback also fails, the pipeline halts. There is no synthetic span generation.
3. **Arize Prompt Registry (Phase 5):** If `upsert-prompt` returns `fetch failed` or HTTP 500, the pipeline halts with `RuntimeError`. The patched prompt is not silently abandoned; the failure is surfaced to the operator via the SSE stream.

The reasoning behind this design is that a system that reports successful remediation while silently failing to deploy the patch provides false confidence. Explicit failure is preferable to undetected partial failure in a security-adjacent pipeline.
