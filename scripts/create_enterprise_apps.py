"""
Create Enterprise Edition Search Apps for FinOps and HR datastores.
Enterprise Edition unlocks extractive_answers / extractive_segments.
"""
import os
from google.cloud import discoveryengine_v1

PROJECT_ID = "aerocaliper"
LOCATION = "global"

def create_enterprise_app(app_id: str, datastore_id: str, display_name: str):
    client = discoveryengine_v1.EngineServiceClient()
    parent = f"projects/{PROJECT_ID}/locations/{LOCATION}/collections/default_collection"
    
    engine = discoveryengine_v1.Engine(
        display_name=display_name,
        solution_type=discoveryengine_v1.SolutionType.SOLUTION_TYPE_SEARCH,
        data_store_ids=[datastore_id],
        search_engine_config=discoveryengine_v1.Engine.SearchEngineConfig(
            search_tier=discoveryengine_v1.SearchTier.SEARCH_TIER_ENTERPRISE,
            search_add_ons=[discoveryengine_v1.SearchAddOn.SEARCH_ADD_ON_LLM],
        ),
    )
    
    print(f"Creating Enterprise app '{app_id}' linked to datastore '{datastore_id}'...")
    op = client.create_engine(parent=parent, engine=engine, engine_id=app_id)
    result = op.result()  # blocks until done
    print(f"✅ Created: {result.name}")
    return result

if __name__ == "__main__":
    create_enterprise_app(
        app_id="finops-app",
        datastore_id="finops-ds",
        display_name="AeroCaliper FinOps Policy Search"
    )
    create_enterprise_app(
        app_id="hr-app",
        datastore_id="hr-ds",
        display_name="AeroCaliper HR Privacy Policy Search"
    )
    print("\nDone. Update env vars:")
    print("  VERTEX_ENGINE_ID_FINOPS=finops-app")
    print("  VERTEX_ENGINE_ID_HR=hr-app")
