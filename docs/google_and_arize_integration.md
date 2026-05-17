# Google Cloud and Arize Integration

AeroCaliper integrates Google Cloud Platform services with Arize Phoenix observability.

## Google Cloud Technologies Utilized

1. **Google Agent Platform SDK (google-genai)**
   - The system utilizes the official Gemini API SDK.
   - All models (gemini-3.1-pro-preview) are executed via Vertex AI routing for security and scale.
   
2. **Google Cloud Run**
   - The primary remediation engine is containerized and hosted on Cloud Run.
   - Cloud Run fulfills the requirement for a Code-Owned Agent Runtime, allowing trace instrumentation.

3. **Google Secret Manager**
   - API keys (GOOGLE_AGENT_PLATFORM_API_KEY, PHOENIX_API_KEY) are stored encrypted at rest.
   - Cloud Run injects these secrets as environment variables during runtime, avoiding local file leakage in production environments.

4. **Google Cloud Logging**
   - Standard stdout print statements are bypassed.
   - AeroCaliper implements google-cloud-logging to stream structured logs directly to the GCP Logs Explorer, enabling native alert configurations.

5. **Google Cloud Model Armor and Cloud Functions**
   - The deep packet inspection mechanism utilizes the google-cloud-modelarmor SDK, validating payloads against enterprise security templates via the SanitizeUserPrompt API.
   - This logic is deployed as an external, HTTP-triggered Google Cloud Function (2nd Gen), implementing a distributed microservice architecture.

6. **Gemini CLI Config**
   - A native gemini-cli-config.json file configures the @arizeai/phoenix-mcp within the Gemini CLI for developer interactions.

7. **Google Cloud Build (CI/CD)**
   - Continuous deployment is managed by Cloud Build triggers.
   - Builds execute using a dedicated, least-privilege user-managed service account (cloudbuild-runner@aerocaliper.iam.gserviceaccount.com).
   - The runner is granted minimal scoped roles: roles/artifactregistry.writer, roles/run.admin, roles/storage.admin, roles/logging.logWriter, and roles/iam.serviceAccountUser.

8. **Vertex AI Search (RAG)**
   - AeroCaliper implements Retrieval-Augmented Generation to fetch enterprise FinOps policies.
   - When the Target Agent violates constraints (e.g., missing budget tags or failing to use Spot instances), Gemini 3.1 Pro is grounded in the official Enterprise_FinOps_Routing_Policy_2026.txt via Vertex AI Search prior to diagnosing the root cause.

## Arize Phoenix Integration

1. **Trace Exporting (OTLP)**
   - The Target Agent and AeroCaliper are instrumented using arize-phoenix-otel and openinference-instrumentation-google-genai.
   - Root-cause logic and LLM-as-a-Judge evaluations are exported to the Phoenix UI.

2. **Arize MCP Server**
   - AeroCaliper runs a programmatic execution of @arizeai/phoenix-mcp using the Python SDK.
   - The get-spans tool fetches the failed execution context from the observability platform.

3. **Autonomous Patching and The Self-Improvement Loop**
   - Following approval, AeroCaliper uses the upsert-prompt MCP tool to deploy a hardened system prompt to the Arize Prompt Registry.
   - The Target Agent dynamically pulls this new prompt on reboot via get_prompt().

4. **Live Evaluations**
   - An LLM-as-a-Judge evaluation pipeline assesses historical traces inside the Phoenix workspace to measure execution accuracy over time.
