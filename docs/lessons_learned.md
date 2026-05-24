# Engineering Notes

Version: v4.0 -- Last audited: 2026-05-24

A record of integration issues, SDK behavior, and design decisions encountered during development.

---

## Google Cloud Platform

### Model Armor -- Regional Endpoint Required

The Model Armor API must be configured with an explicit regional endpoint:

```python
ClientOptions(api_endpoint="modelarmor.us-central1.rep.googleapis.com")
```

Omitting this and relying on the global endpoint results in `404 Not Found` or `TEMPLATE_NOT_FOUND` errors even when the template exists and is correctly configured. The global endpoint does not route to the regional Model Armor service.

Template propagation delay: Templates created via SDK or console may take several minutes to become queryable at the regional endpoint. Running integration tests immediately after template creation may produce `TEMPLATE_NOT_FOUND`. A retry with a delay resolves this.

The initial implementation included a local regex fallback in `AgentGatewaySimulator`. This was removed. The constructor now raises `RuntimeError` if the SDK or credentials are absent, requiring developers to configure the dependency correctly rather than silently bypassing it.

### Vertex AI Search -- Indexing Delay

Creating a datastore and importing a document does not make the document immediately queryable. The Vertex AI backend processes, chunks, and indexes documents asynchronously. This can take 10 to 30 minutes for unstructured documents.

Staging documents in Cloud Storage (`gs://aerocaliper-rag-bucket`) and importing from GCS is more reliable than direct uploads through the console, which can encounter permission or workspace issues.

For Extractive Answers, the query must target the engine-level serving config path (`/engines/{engine_id}/servingConfigs/default_config`), not the datastore-level path. Using the datastore-level path returns results without extractive answer content, which is not detectable from the response status code.

All hardcoded policy fallbacks were removed. If `discoveryengine_v1` returns zero extractive answers, the pipeline raises `RuntimeError`.

### Google Cloud Logging -- Environment Gating

Enabling `google-cloud-logging` unconditionally caused credential resolution errors and increased startup time in local development. The `gcp_print()` wrapper gates Cloud Logging export behind `ENABLE_CLOUD_LOGGING=true`. Local output remains identical to Cloud Run output.

### Cloud Build -- Service Account Scope

The default Cloud Build service account grants broader permissions than required. A dedicated `cloudbuild-runner` service account with the minimum required roles was created to limit the blast radius of a compromised build pipeline.

---

## Arize and Phoenix

### Package Disambiguation

The `arize` PyPI package targets the Arize AX enterprise platform. The open-source observability stack, prompt registry, and local tracing require separate packages: `arize-phoenix`, `arize-phoenix-client`, and `arize-phoenix-otel`. Installing only `arize` and attempting to use `phoenix` modules will fail with import errors.

### Prompt Registry API -- prompt_identifier Parameter

Older documentation and community examples reference `client.prompts.get(name="prompt-name")`. The `name` keyword argument was removed from the `Prompts.get()` method in newer versions of the `arize-phoenix-client` package. The correct signature is:

```python
client.prompts.get(prompt_identifier="your-prompt-name")
```

Using `name=` produces `TypeError: Prompts.get() takes 1 positional argument but 2 were given`.

### MCP Integration -- Dynamic Space Routing

Hardcoding the Phoenix space URL suffix (for example, `/s/myworkspace`) in the MCP `--baseUrl` argument causes failures when the workspace ID changes or when the project is shared across team members with different space IDs. The workspace suffix must be injected at runtime via `ARIZE_SPACE_ID`.

### MCP on Windows -- npx Wrapping Required

The `npx` command is not directly executable on Windows via `subprocess.Popen` or `StdioServerParameters`. Attempting to set `command="npx"` on Windows results in a `FileNotFoundError` that manifests as an MCP connection timeout with no diagnostic output. The correct approach on Windows:

```python
StdioServerParameters(command="cmd.exe", args=["/c", "npx", "-y", "@arizeai/phoenix-mcp", ...])
```

Platform detection in `aerocaliper.py` switches between the two forms automatically.

### upsert-prompt 500 Errors -- Fail-Closed

The Arize Cloud `upsert-prompt` endpoint may return `fetch failed` or HTTP 500 depending on API auth state and workspace configuration. This error is treated as a fatal failure. The pipeline raises `RuntimeError` rather than logging a warning and continuing. A silent failure here would leave the target agent running with its vulnerable prompt while the system reports successful remediation.

---

## Empirical Backtesting

### Cross-Domain Dataset Contamination

Running the full `golden_dataset.csv` against a FinOps patch causes HR-specific cases to be evaluated against FinOps compliance criteria, producing incorrect failures. Phase 4 filters the dataset to the active domain before simulation. Pass rate is computed over the filtered denominator only. This is enforced in `evaluators.py` via the domain tag on each row.

### JSON Parse Failures in Simulation

Gemini occasionally wraps its output in markdown code fences (` ```json ... ``` `). The backtester strips these before calling `json.loads()`. On the first attempt, if the model returns conversational text instead of JSON, all cases in that attempt fail to parse and are recorded as failures. The refinement prompt for attempt 2 explicitly instructs the model to return only valid JSON, which resolves this in practice.

### Optimization Loop -- 3-Attempt Cap

A single backtest attempt is insufficient to converge on edge cases without iteration. The 3-attempt cap was set empirically: in practice, a well-formed candidate prompt either passes on attempt 1 or converges by attempt 2 after a refinement call that appends the failure context. Extending the cap beyond 3 has diminishing returns and increases pipeline execution time significantly.

### Async Event Loop -- to_thread and sleep

Blocking Gemini calls inside async generator functions stall the FastAPI SSE event loop, causing the frontend to receive no updates during long inference operations. All `ask_gemini()` calls in async paths are wrapped with `await asyncio.to_thread(self.ask_gemini, ...)`. `await asyncio.sleep(0)` is inserted before blocking calls to flush the SSE buffer and ensure preceding log events are delivered before the blocking operation starts.
