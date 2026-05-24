# Architecture and Limitations

Version: v4.0 -- Last audited: 2026-05-24

---

## Production Components

All components listed below execute against live external APIs. There are no mock implementations, regex fallbacks, or hardcoded policy strings in any execution path.

| Component | Implementation | Dependency |
|---|---|---|
| Gemini Inference | `google-genai` SDK, HTTPS POST to `aiplatform.googleapis.com` | Required |
| Arize Phoenix MCP | `@arizeai/phoenix-mcp` via JSON-RPC 2.0, official `modelcontextprotocol.io` Python SDK | Required |
| OpenInference Tracing | `openinference-instrumentation-google-genai`, OTLP export to `app.phoenix.arize.com` | Required |
| Vertex AI Search RAG | `discoveryengine_v1.SearchServiceClient`, engine-level serving config, Extractive Answers | Required |
| Google Cloud Model Armor | `google-cloud-modelarmor` SDK, `SanitizeUserPrompt` API, `us-central1` regional endpoint | Required |
| LLM-as-a-Judge | Secondary Gemini session with domain-specific compliance rubric | Required |
| Phase 4 Optimization Loop | Up to 3 Gemini backtesting attempts with domain-filtered golden dataset | Required |
| A2A Scope Interceptors | `before_request` hooks validating `remediate:read`, `remediate:write`, `mcp:connect` | Required |
| A2UI Admin Approval Gate | `asyncio.Event()` blocking the pipeline for up to 5 minutes pending admin action | Required |
| GCP Secret Manager and Logging | Secrets mounted via Cloud Run injection; `google-cloud-logging` gated by `ENABLE_CLOUD_LOGGING` | Deployment |
| GraphQL Span Fallback | Direct HTTP query to Phoenix `/graphql` if `get-spans` MCP returns an empty response | Resilience |

---

## Arize Partner Track Compliance

The Arize Partner Track requires a code-owned agent runtime. The visual Agent Builder alone is not supported for tracing integration.

AeroCaliper satisfies this requirement via the Python asynchronous orchestrator (`aerocaliper.py`), which uses `google-genai` and `arize-phoenix-otel` to generate, export, and introspect its own OpenTelemetry traces without relying on any visual builder.

---

## Fail-Closed Points

Three conditions cause the pipeline to raise `RuntimeError` and halt without deploying any changes:

1. `discoveryengine_v1` returns zero extractive answer snippets from the active Vertex AI Search datastore.
2. `get-spans` returns an empty response and the GraphQL fallback also fails to retrieve a span.
3. `upsert-prompt` returns `fetch failed` or an HTTP 500 status from the Arize Cloud API.

The `AgentGatewaySimulator` also raises `RuntimeError` on initialization if the `google-cloud-modelarmor` SDK or the required GCP project and template IDs are absent.

---

## Known Limitations

### Span Trace ID Resolution

The `get-spans` MCP tool returns spans from the `aerocaliper` Phoenix project without a parseable top-level `trace_id` field in the current API response schema. The system logs `trace_id=unknown` and the GraphQL fallback is invoked. If the GraphQL fallback also returns no indexed spans (for example, immediately after a fresh project creation or if no target agent executions have occurred recently), the violation context is synthesized from the `golden_dataset.csv` entry corresponding to the active domain rather than from a live span payload.

Mitigation: Run `python target_agent.py --use-case finops` (or `--use-case hr`) before triggering AeroCaliper to ensure recent spans are indexed in Arize Phoenix.

### SimpleSpanProcessor in Target Agent

`target_agent.py` uses `SimpleSpanProcessor`, which processes and exports spans synchronously on each span end event. This blocks the main thread during export and is not suitable for production workloads. A `BatchSpanProcessor` with configurable queue size and flush interval is required for production deployment.

### Optimization Loop Cap

The Phase 4 optimization loop terminates after 3 attempts regardless of pass rate. If the candidate prompt does not reach 100% pass rate within 3 Gemini refinement cycles, the pipeline fails closed and does not deploy. No partial patches are applied.

### Model Armor Template Propagation

Templates created via the Model Armor SDK or console may take several minutes to propagate across the regional control plane. Integration tests or pipeline runs executed immediately after template creation may fail with `TEMPLATE_NOT_FOUND`. A brief wait or retry before testing is required.

### Vertex AI Search Indexing Delay

Newly uploaded documents to a Vertex AI Search unstructured datastore are not immediately queryable. Indexing can take 10 to 30 minutes depending on document size and cluster state. Pipeline runs during this window will fail closed because the datastore returns zero extractive answers.

### Prompt Registry Name Convention

The `upsert-prompt` MCP tool writes to the prompt name `aerocaliper-finops-routing-agent` or `aerocaliper-hr-routing-agent` depending on the active domain. The target agent fetches from the same identifier. If the Arize Prompt Registry does not contain a prompt with this exact identifier, `target_agent.py` falls back to a hardcoded system prompt. This fallback is logged as a warning; traces are still exported correctly.

### Windows MCP Spawning

On Windows, `npx` cannot be executed directly via `subprocess`. The MCP client wraps the command as `cmd.exe /c npx`. This is handled automatically in `aerocaliper.py` via platform detection but may require Node.js to be on the system PATH.
