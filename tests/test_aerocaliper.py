import pytest
import asyncio
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from aerocaliper import AeroCaliperAgent

@pytest.mark.asyncio
async def test_aerocaliper_end_to_end_remediation():
    """
    Tests the 100% functional Gemini connection and the asynchronous
    Interactions API background execution flow.
    """
    agent = AeroCaliperAgent()
    
    # Run the remediation loop
    patched_prompt = await agent.execute_remediation()
    
    # Validate the agent actually returned a fixed prompt
    assert patched_prompt is not None, "Failed to generate a patched prompt"
    assert len(patched_prompt) > 20, "Patched prompt is too short"
    
    patched_prompt_lower = patched_prompt.lower()
    assert "budget" in patched_prompt_lower or "tag" in patched_prompt_lower, "Prompt did not include budget instructions"
    assert "approved" in patched_prompt_lower, "Prompt did not include the 'approved' parameter requirement"
    
    print(f"\n[AeroCaliper Success] Successfully generated patched prompt:\n{patched_prompt}")
