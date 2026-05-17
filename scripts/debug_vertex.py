import os
from google.cloud import discoveryengine_v1
from dotenv import load_dotenv

def debug_vertex():
    load_dotenv()
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT") or "aerocaliper"
    location = os.getenv("VERTEX_SEARCH_LOCATION", "global")
    data_store_id = os.getenv("VERTEX_DATASTORE_ID")
    
    print(f"Project: {project_id}, Location: {location}, Datastore: {data_store_id}")
    
    client = discoveryengine_v1.SearchServiceClient()
    serving_config = client.serving_config_path(project_id, location, data_store_id, "default_config")
    
    request = discoveryengine_v1.SearchRequest(
        serving_config=serving_config,
        query="HR Privacy PII Salary Restrictions",
        page_size=1,
    )
    
    try:
        response = client.search(request)
        for result in response.results:
            print("Document Name:", result.document.name)
            print("Struct Data:", result.document.struct_data)
            print("Full Document:", result.document)
            return
        print("No results.")
    except Exception as e:
        print("Error:", e)

if __name__ == "__main__":
    debug_vertex()
