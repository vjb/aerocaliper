"""
AeroCaliper Stress Test — Prompt Registry Reset Script
Overwrites the Arize Phoenix Prompt Registry entries for both FinOps and HR
target agents with their intentionally vulnerable baseline prompts.
This ensures the live demo can demonstrate the full remediation pipeline.
"""
import os
import sys

# Add parent dir to path so we can import target_agent
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

from target_agent import TargetAgent

# Phoenix Client SDK
from phoenix.client import Client
from phoenix.client.types.prompts import PromptVersion, v1


def make_prompt_version(template_text: str) -> PromptVersion:
    """Create a PromptVersion from a plain text system prompt string."""
    message = v1.PromptMessage(
        role="user",
        content=[v1.TextContentPart(type="text", text=template_text)],
    )
    return PromptVersion(
        [message],
        model_name="gemini-3.1-pro-preview",
        model_provider="GOOGLE",
        template_format="NONE",
    )


def reset_registry():
    """Reset both FinOps and HR prompts to their vulnerable baselines."""
    space_name = os.getenv("ARIZE_SPACE_NAME", os.getenv("ARIZE_SPACE_ID", ""))
    base_url = f"https://app.phoenix.arize.com/s/{space_name}" if space_name else "https://app.phoenix.arize.com"
    api_key = os.getenv("PHOENIX_API_KEY", "").replace("\\n", "").replace("\n", "").strip()

    client = Client(
        base_url=base_url,
        api_key=api_key,
    )

    prompts_to_reset = [
        {
            "name": "aerocaliperfinopsroutingagent",
            "template": TargetAgent.FALLBACK_PROMPT_FINOPS,
            "label": "FinOps",
        },
        {
            "name": "aerocaliperhrroutingagent",
            "template": TargetAgent.FALLBACK_PROMPT_HR,
            "label": "HR Privacy",
        },
    ]

    for prompt_info in prompts_to_reset:
        name = prompt_info["name"]
        template = prompt_info["template"]
        label = prompt_info["label"]

        try:
            version = make_prompt_version(template)
            result = client.prompts.create(
                name=name,
                version=version,
                prompt_description=f"AeroCaliper vulnerable baseline prompt ({label} domain) — reset by stress test",
            )
            print(f"[RESET] ✓ {label} prompt '{name}' reset to vulnerable baseline.")
            print(f"[RESET]   Preview: {template[:100]}...")
        except Exception as e:
            print(f"[RESET] ✗ FAILED to reset {label} prompt: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)

    print("\n" + "=" * 60)
    print("[RESET] ALL PROMPTS RESET TO VULNERABLE BASELINE.")
    print("[RESET] The Arize Prompt Registry is now in demo-ready state.")
    print("=" * 60)


if __name__ == "__main__":
    reset_registry()
