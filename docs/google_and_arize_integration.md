# Google Cloud & Arize Partner Track Integration

AeroCaliper is built from the ground up to deeply integrate Google Cloud Platform services with Arize Phoenix observability. 

## Google Cloud Technologies Utilized

1. **Google Agent Platform SDK (`google-genai`)**
   - We utilize the official, unified Gemini API SDK.
   - All models (`gemini-3.1-pro-preview`) are executed via Vertex AI routing for enterprise security and scale.
   
2. **Google Cloud Run (Serverless Microservices)**
   - The primary autonomous remediation engine is fully containerized and hosted securely on Cloud Run.
   - We explicitly chose Cloud Run to fulfill the Arize track's strict requirement for a **Code-Owned Agent Runtime** (bypassing visual agent builders to allow deep trace instrumentation).

3. **Google Secret Manager**
   - API keys (`GOOGLE_AGENT_PLATFORM_API_KEY`, `PHOENIX_API_KEY`) are stored encrypted at rest.
   - Cloud Run dynamically injects these secrets as environment variables during runtime, avoiding `.env` leakage in production.

4. **Google Cloud Logging**
   - Standard stdout `print()` statements are bypassed.
   - AeroCaliper implements `google-cloud-logging` to stream structured logs directly to the GCP Logs Explorer, enabling native alert configurations.

5. **Google Cloud Functions (Distributed Gateway)**
   - Our deep packet inspection mechanism (simulating Cloud Armor / Model Armor rules) is deployed as an external, HTTP-triggered Google Cloud Function (2nd Gen).
   - This proves our microservice architecture, allowing independent scaling of the inspection gateway vs the orchestration engine.

6. **Gemini CLI Config**
   - We include a native `gemini-cli-config.json` that drops `@arizeai/phoenix-mcp` into the Gemini CLI for manual developer interaction, precisely as the Arize track rubric requires.

## Arize Phoenix Integration

1. **Trace Exporting (OTLP)**
   - The Target Agent and AeroCaliper itself are instrumented using `arize-phoenix-otel` and `openinference-instrumentation-google-genai`.
   - Complex root-cause logic and LLM-as-a-Judge evaluations are completely visible in the Phoenix UI.

2. **Arize MCP Server**
   - AeroCaliper runs a programmatic, headless execution of `@arizeai/phoenix-mcp` using the official Python SDK.
   - We utilize `get-spans` to fetch hallucinating context directly from the observability platform.

3. **Autonomous Patching & The Self-Improvement Loop**
   - Once a fix is approved, AeroCaliper uses the `upsert-prompt` MCP tool to deploy a hardened system prompt directly to the Arize Prompt Registry.
   - The Target Agent is configured to dynamically pull this new prompt on reboot (`get_prompt()`), closing the autonomous loop perfectly.

4. **Live Evaluations**
   - An LLM-as-a-Judge evaluation pipeline assesses the historical traces inside the Phoenix workspace to score hallucination reduction over time.
