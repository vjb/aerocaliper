import os
import sys
from dotenv import load_dotenv

load_dotenv()

import pytest
from unittest.mock import patch, MagicMock

@patch("google.cloud.discoveryengine_v1.SearchServiceClient")
def test_vertex_search(mock_client_class):
    mock_client = mock_client_class.return_value
    mock_response = MagicMock()
    mock_result = MagicMock()
    mock_result.document.derived_struct_data = {"extractive_answers": [{"content": "Matched Snippet"}]}
    mock_response.results = [mock_result]
    mock_client.search.return_value = mock_response

    print("Testing Vertex AI Search Data Store...")
    os.environ["GOOGLE_CLOUD_PROJECT"] = "test-project"
    os.environ["VERTEX_SEARCH_LOCATION"] = "global"
    os.environ["VERTEX_DATASTORE_ID"] = "test-ds"

    try:
        from google.cloud import discoveryengine_v1 as discoveryengine
        client = discoveryengine.SearchServiceClient()
        serving_config = f"projects/test-project/locations/global/collections/default_collection/dataStores/test-ds/servingConfigs/default_config"
        
        request = discoveryengine.SearchRequest(
            serving_config=serving_config,
            query="FinOps Routing Policy Spot Instances Budget Tag",
            page_size=1,
        )
        
        response = client.search(request)
        snippets = []
        for result in response.results:
            for ext in result.document.derived_struct_data.get("extractive_answers", []):
                snippets.append(ext.get("content", ""))
        
        assert "Matched Snippet" in snippets
        print(f"PASS: Found snippets: {snippets}")
    except Exception as e:
        pytest.fail(f"FAIL: Exception: {e}")
