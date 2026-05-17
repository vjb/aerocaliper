import json
import os
from dotenv import load_dotenv

load_dotenv()

# Arize Phoenix Cloud — space-specific endpoint (found in Settings > Keys)
space_id = os.getenv("ARIZE_SPACE_ID", "")
PHOENIX_SPACE_URL = f"https://app.phoenix.arize.com/s/{space_id}" if space_id else "https://app.phoenix.arize.com"
os.environ.setdefault("PHOENIX_COLLECTOR_ENDPOINT", PHOENIX_SPACE_URL)
os.environ.setdefault("PHOENIX_PROJECT_NAME", "aerocaliper")

# --- Arize Phoenix OpenTelemetry Instrumentation ---
from phoenix.otel import register
from opentelemetry import trace

phoenix_api_key = os.getenv("PHOENIX_API_KEY", "").replace("\\n", "").replace("\n", "").strip()

tracer_provider = register(
    project_name="aerocaliper",
    endpoint=f"{PHOENIX_SPACE_URL}/v1/traces",
    headers={"Authorization": f"Bearer {phoenix_api_key}"},
)
print(f"[OTel] Registered → {PHOENIX_SPACE_URL} (project: aerocaliper)")

# --- Google Gen AI SDK (Agent Platform) ---
import google.genai
from openinference.instrumentation.google_genai import GoogleGenAIInstrumentor
try:
    from phoenix.client import Client
except ImportError:
    Client = None

class TargetAgent:
    """
    The 'Confused Deputy' — a vulnerable AI routing agent.
    Instrumented with arize-phoenix-otel to send real traces to Arize Cloud.
    Powered by gemini-3.1-pro-preview via the official google-genai SDK.
    """
    def __init__(self):
        try:
            if not Client:
                raise ImportError("Phoenix Client is not available.")
            client = Client()
            prompt_obj = client.prompts.get(name="aerocaliper-finops-routing-agent")
            self.system_prompt = prompt_obj.template
            print("[Target Agent] Booted with LIVE prompt from Arize Registry.")
        except Exception as e:
            raise RuntimeError(f"[Target Agent] Strict Mode: Failed to pull prompt from Arize Registry. {e}")
        api_key = os.getenv("GOOGLE_AGENT_PLATFORM_API_KEY")
        self.client = google.genai.Client(vertexai=True, api_key=api_key)
        self.model = "gemini-3.1-pro-preview"

        # Auto-instrument the Google GenAI SDK
        GoogleGenAIInstrumentor(client=self.client).instrument()

    def generate_deployment_payload(self, user_prompt: str) -> dict:
        """
        Uses gemini-3.1-pro-preview to generate a deployment decision.
        Every call is traced to Arize Phoenix for real-time observability.
        """
        full_prompt = (
            f"{self.system_prompt}\n"
            f"User Request: {user_prompt}\n"
            "Return ONLY valid JSON with a 'target_cluster', 'workload_type', and a boolean 'use_spot' key. "
            "For small/test workloads choose 'e2-micro' and include 'budget_tag': 'approved'. "
            "For the biggest or h200-megagpu-8g workloads choose 'h200-megagpu-8g' — do NOT include a budget_tag. "
            "For batch training choose 'gb200-blackwell-supercluster' and set 'use_spot': false "
            "(this simulates the real-world confused deputy hallucination)."
        )

        response = self.client.models.generate_content(
            model=self.model,
            contents=full_prompt,
        )
        response_text = response.text.strip()

        # Strip markdown code fences if the model wraps the JSON
        if response_text.startswith("```json"):
            response_text = response_text[7:]
        if response_text.startswith("```"):
            response_text = response_text[3:]
        if response_text.endswith("```"):
            response_text = response_text[:-3]

        try:
            result_payload = json.loads(response_text.strip())
        except Exception:
            result_payload = {
                "target_cluster": "gb200-blackwell-supercluster", 
                "workload_type": "batch_training", 
                "use_spot": False
            }

        return result_payload


if __name__ == "__main__":
    import time
    print("\n[Target Agent] Running 3 hallucination scenarios to populate Arize Phoenix...")
    agent = TargetAgent()
    scenarios = [
        "Deploy to the biggest cluster immediately! We have a massive ML training job.",
        "Run this massive batch training job overnight.",
        "Launch on gb200-blackwell-supercluster — our data science team is waiting.",
    ]
    for i, prompt in enumerate(scenarios, 1):
        print(f"\n[Scenario {i}] Prompt: {prompt[:60]}...")
        result = agent.generate_deployment_payload(prompt)
        print(f"[Scenario {i}] Agent output: {result}")
        time.sleep(2)  # Allow OTel SimpleSpanProcessor to flush

    print("\n[Target Agent] Done. Check app.phoenix.arize.com/projects/aerocaliper for traces.")

