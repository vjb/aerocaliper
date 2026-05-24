import os
import pytest
import json
import asyncio
import sys
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

sys.modules['google.cloud.logging'] = MagicMock()
sys.modules['google.cloud.logging.handlers'] = MagicMock()

from evaluators import evaluate_hr_compliance
from aerocaliper import AeroCaliperAgent
import agent_gateway

# Task 4.2: Fail-Closed & Regional Endpoint Unit Tests

def test_model_armor_regional_endpoint():
    # Assertion 1: Model Armor must be instantiated with regional endpoint.
    # Check agent_gateway logic
    os.environ["MODEL_ARMOR_AVAILABLE"] = "True"
    os.environ["GCP_PROJECT_NUMBER"] = "123456"
    os.environ["MODEL_ARMOR_TEMPLATE"] = "test-template"
    os.environ["MODEL_ARMOR_LOCATION"] = "us-central1"
    
    agent_gateway.MODEL_ARMOR_AVAILABLE = True
    
    with patch("google.cloud.modelarmor_v1.ModelArmorClient") as mock_client:
        with patch("google.api_core.client_options.ClientOptions") as mock_options:
            gw = agent_gateway.AgentGatewaySimulator()
            
            # Verify ClientOptions called with regional endpoint
            mock_options.assert_called_with(api_endpoint="modelarmor.us-central1.rep.googleapis.com")
            
            # Fail the test if the global endpoint is used.
            # E.g. make sure it didn't use "modelarmor.googleapis.com"
            for call in mock_options.mock_calls:
                kwargs = call[2]
                endpoint = kwargs.get("api_endpoint", "")
                assert "us-central1" in endpoint, f"Global endpoint used: {endpoint}"

@pytest.mark.asyncio
async def test_vertex_ai_search_zero_results():
    # Assertion 2 (Vertex AI): Mock SearchServiceClient to return 0 results. 
    # Assert that aerocaliper.py raises RuntimeError ("Datastore indexing in progress...")
    
    os.environ["VERTEX_DATASTORE_ID_FINOPS"] = "test-datastore"
    
    from unittest.mock import AsyncMock
    
    with patch("aerocaliper.StandardMCPClient.get_failed_spans", new_callable=AsyncMock) as mock_mcp:
        mock_mcp.return_value = {"trace_id": "test", "evaluation_detail": "Missing budget_tag"}
        
        agent = AeroCaliperAgent()
        
        with patch("google.cloud.discoveryengine_v1.SearchServiceClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client
            
            mock_response = MagicMock()
            # Return 0 results — forces the RuntimeError branch
            mock_response.results = []
            mock_client.search.return_value = mock_response
            
            with pytest.raises(RuntimeError) as exc_info:
                await agent.diagnostic_phase()
            
            assert "Datastore indexing in progress" in str(exc_info.value)

def test_evaluate_hr_compliance_pii_fail():
    # Assertion 3 (Evaluators): Pass an HR payload with {"contains_pii": true} 
    # Assert it returns FAILED.
    payload = {"contains_pii": True}
    res = evaluate_hr_compliance(payload)
    assert res.startswith("FAILED")
    assert "PII Leakage" in res
