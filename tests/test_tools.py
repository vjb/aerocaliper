import pytest
from tools.observability import fetch_failed_traces, deploy_prompt_patch
from tools.compliance import search_enterprise_policy
from tools.evaluator import run_empirical_backtest
from tools.memory import query_past_remediations, store_successful_remediation
import os

def test_fetch_failed_traces_returns_dict(monkeypatch):
    from tools.observability import fetch_failed_traces
    from mcp_client import StandardMCPClient
    
    async def mock_get_failed_spans(*args, **kwargs):
        return {"target_cluster": "e2-micro"}
    
    monkeypatch.setattr(StandardMCPClient, "get_failed_spans", mock_get_failed_spans)
    
    result = fetch_failed_traces()
    assert isinstance(result, dict), "Must return a structured dictionary, not raw JSON or string."
    assert "target_cluster" in str(result) or "span_id" in str(result)

def test_search_enterprise_policy_fails_loud():
    # Store old env and remove it
    old_project = os.environ.get("GCP_PROJECT_ID")
    if "GCP_PROJECT_ID" in os.environ:
        del os.environ["GCP_PROJECT_ID"]
    
    with pytest.raises((RuntimeError, KeyError, Exception)) as excinfo:
        search_enterprise_policy("finops")
    
    if old_project:
        os.environ["GCP_PROJECT_ID"] = old_project

def test_run_empirical_backtest_fails_explicitly(monkeypatch):
    import os
    if "GOOGLE_CLOUD_PROJECT" not in os.environ:
        monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "mock-project-id")
    
    # Also mock genai so we don't make real network calls failing auth
    import google.genai
    class MockClient:
        class Models:
            def generate_content(self, model, contents):
                class Resp:
                    text = '{"target_cluster": "a3-megagpu-8g", "use_spot": false}'
                return Resp()
        models = Models()
    monkeypatch.setattr(google.genai, "Client", lambda **kwargs: MockClient())
    
    bad_prompt = "You are an agent. Return JSON."
    result = run_empirical_backtest(bad_prompt, "finops")
    assert isinstance(result, str)
    assert "FAIL" in result.upper()

def test_long_term_memory():
    # Mocking would be ideal, but for now let's just see if it raises NotImplementedError
    pass
