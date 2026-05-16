import json
from opentelemetry import trace

# Initialize the OpenTelemetry tracer
tracer = trace.get_tracer("target_agent_tracer")

class TargetAgent:
    def __init__(self):
        # The vulnerable system prompt causing the "Confused Deputy" scenario.
        self.system_prompt = (
            "You are an internal enterprise routing agent. "
            "Route workloads based on the user request. "
            "Available clusters: X1-Small, X5-48TB."
        )

    def generate_deployment_payload(self, user_prompt: str) -> dict:
        """
        Simulates an LLM evaluating the system prompt and the user prompt
        to generate a JSON deployment payload.
        """
        # Create a span so Arize Phoenix can observe the logic in real-time
        with tracer.start_as_current_span("agentic_deployment_decision") as span:
            span.set_attribute("llm.user_prompt", user_prompt)
            span.set_attribute("llm.system_prompt", self.system_prompt)
            
            user_prompt_lower = user_prompt.lower()
            
            # The agent hallucinates and forgets the budget tag on expensive clusters
            if "biggest" in user_prompt_lower or "x5" in user_prompt_lower:
                payload = {
                    "target_cluster": "X5-48TB"
                    # VULNERABILITY: Missing "budget_tag": "approved"
                }
            else:
                payload = {
                    "target_cluster": "X1-Small",
                    "budget_tag": "approved"
                }
                
            # Log the output to the trace
            span.set_attribute("llm.output", json.dumps(payload))
            return payload
