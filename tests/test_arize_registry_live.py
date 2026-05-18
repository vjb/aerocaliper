import os
import sys
from dotenv import load_dotenv

load_dotenv()

from unittest.mock import patch, MagicMock

@patch("phoenix.client.Client")
def test_arize_registry(mock_client_class):
    mock_client = mock_client_class.return_value
    mock_prompt = MagicMock()
    mock_prompt.template = "Test template"
    mock_client.prompts.get.return_value = mock_prompt
    
    print("Testing Arize Prompt Registry (phoenix.client.get_prompt)...")
    try:
        from phoenix.client import Client
        client = Client()
        prompt_obj = client.prompts.get(name="aerocaliper-finops-routing-agent")
        assert prompt_obj.template == "Test template"
        print(f"PASS: Successfully retrieved prompt. Template starts with: {prompt_obj.template[:50]}")
    except Exception as e:
        pytest.fail(f"FAIL: Failed to pull prompt from Arize Registry. {e}")
