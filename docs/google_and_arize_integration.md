# Google Cloud and Arize Integration

Version: v4.0 -- Last audited: 2026-05-24

---

## Google Cloud Technologies

### 1. Gemini Inference (google-genai SDK)

All LLM inference is executed via HTTPS POST to `aiplatform.googleapis.com` using the `google-genai` SDK. Gemini drives four distinct operations within the pipeline:

- Phase 3: Root-cause analysis of the failed agent trace combined with the Vertex AI Search policy snippet.
- Phase 4 (simulation): Backtesting each golden dataset case against the candidate prompt.
- Phase 4 (refinement): Generating a revised candidate prompt when backtesting cases fail.
- Phase 4 (judge): Evaluating the approved candidate prompt against the compliance rubric.

All Gemini calls in async execution paths are wrapped in `asyncio.to_thread()` to prevent blocking the FastAPI event loop and stalling the SSE stream.

### 2. Vertex AI Search (RAG)

Two Vertex AI Search engines are provisioned:

- `finops-app`: Indexes the Enterprise FinOps Routing Policy document.
- `hr-app`: Indexes the Enterprise HR Privacy and PII Policy document.

Queries use `discoveryengine_v1.SearchServiceClient` targeting engine-level serving configs (`/engines/{engine_id}/servingConfigs/default_config`) to enable Extractive Answers. Datastore-level serving configs do not return extractive answer content. The distinction is required for this feature.

The active engine is selected at runtime from `VERTEX_ENGINE_ID_FINOPS` or `VERTEX_ENGINE_ID_HR` based on `target_use_case`. If the query returns zero snippets, the pipeline raises `RuntimeError`. Documents imported to a datastore require 10 to 30 minutes to index before queries return results.

### 3. Google Cloud Model Armor

`agent_gateway.py` uses the `google-cloud-modelarmor` SDK to submit the candidate prompt to the `SanitizeUserPrompt` API before deployment. The SDK is configured with:

```python
ClientOptions(api_endpoint="modelarmor.us-central1.rep.googleapis.com")
```

The template ID is read from `MODEL_ARMOR_TEMPLATE`. If the SDK, GCP project ID, or template ID are absent at initialization, `AgentGatewaySimulator.__init__()` raises `RuntimeError`. There is no local regex fallback.

Template propagation delay: Templates created via SDK or console may not be immediately available. A delay of several minutes may be required before the template is queryable at the regional endpoint.

If `GATEWAY_URL` is set, the payload is additionally forwarded to an external HTTP-triggered Cloud Function (2nd Gen) before the MCP upsert.

### 4. Google Cloud Logging

`gcp_print()` in `aerocaliper.py` routes output to both `stdout` and the `google-cloud-logging` SDK simultaneously. Cloud Logging export is gated by `ENABLE_CLOUD_LOGGING=true`. When this variable is absent or false, only `stdout` is used, which avoids credential noise during local development.

### 5. Google Cloud Run

The pipeline is containerized via `Dockerfile` and deployed to Cloud Run. Cloud Run injects secrets from Google Secret Manager as environment variables (`GOOGLE_AGENT_PLATFORM_API_KEY`, `PHOENIX_API_KEY`) at runtime. This avoids storing credentials in the container image or local files.

### 6. Cloud Build CI/CD

`cloudbuild.yaml` defines the build and deployment pipeline. Builds execute using a dedicated service account (`cloudbuild-runner@aerocaliper.iam.gserviceaccount.com`) with the following roles only:

- `roles/artifactregistry.writer`
- `roles/run.admin`
- `roles/storage.admin`
- `roles/logging.logWriter`
- `roles/iam.serviceAccountUser`

### 7. Gemini CLI Configuration

`gemini-cli-config.json` configures the `@arizeai/phoenix-mcp` server within the Gemini CLI for local developer testing.

---

## Arize Phoenix Integration

### 1. OTLP Trace Export

Both `target_agent.py` and `aerocaliper.py` are instrumented with `arize-phoenix-otel` and `openinference-instrumentation-google-genai`. Traces are exported via OTLP HTTP to:

```
https://app.phoenix.arize.com/s/{ARIZE_SPACE_ID}/v1/traces
```

The target agent exports to the `aerocaliper` project. The remediation engine exports to `aerocaliper-remediation-engine`. The OTLP endpoint is constructed dynamically from `ARIZE_SPACE_ID` at runtime.

### 2. MCP Server Connection

`aerocaliper.py` spawns `@arizeai/phoenix-mcp` using `mcp.ClientSession` and `StdioServerParameters` from the `modelcontextprotocol.io` Python SDK. The server process is started with:

- Windows: `command="cmd.exe"`, `args=["/c", "npx", "-y", "@arizeai/phoenix-mcp", "--baseUrl", ..., "--apiKey", ...]`
- Unix: `command="npx"`, `args=["-y", "@arizeai/phoenix-mcp", ...]`

The `--baseUrl` is constructed from `ARIZE_SPACE_ID`. The `--apiKey` is read from `PHOENIX_API_KEY` or `ARIZE_API_KEY`.

### 3. MCP Tool Usage

| Tool | Phase | Behavior on Failure |
|---|---|---|
| `get-projects` | 2.5 | Logs result; does not fail-close on its own |
| `get-datasets` | 2.5 | Logs result; does not fail-close on its own |
| `get-spans` | 3 | Falls back to GraphQL query; raises `RuntimeError` if both fail |
| `upsert-prompt` | 5 | Raises `RuntimeError` on HTTP 500 or `fetch failed` |

### 4. GraphQL Span Fallback

If `get-spans` returns an empty list or a transport error, `aerocaliper.py` sends a GraphQL query directly to `https://app.phoenix.arize.com/graphql` targeting the `aerocaliper` project. This query retrieves the most recent span nodes. If the GraphQL query also returns no results, the pipeline raises `RuntimeError`.

### 5. Prompt Registry

`upsert-prompt` writes the verified candidate patch to the Arize Prompt Registry under the identifier `aerocaliper-finops-routing-agent` (FinOps domain) or `aerocaliper-hr-routing-agent` (HR domain). The target agent reads from this identifier at boot via:

```python
client.prompts.get(prompt_identifier=f"aerocaliper-{use_case}-routing-agent")
```

If the identifier does not exist in the registry, the target agent falls back to a hardcoded placeholder prompt and logs a warning. Traces are still exported correctly in this state.

### 6. LLM-as-a-Judge via Phoenix Evaluations

The Phase 4 judge uses the Vertex AI Search extractive answer retrieved in Phase 3 as the ground truth compliance clause. A separate Gemini session receives the universal rubric, the policy clause, and the candidate prompt, and returns a binary `YES` or `NO` verdict. Evaluation rubrics for both domains are defined in `evaluators.py`.
