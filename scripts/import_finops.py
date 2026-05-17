import os
from google.cloud import discoveryengine_v1
from google.api_core.client_options import ClientOptions

def import_finops():
    project_id = "aerocaliper"
    location = "global"
    data_store_id = "finops-ds"
    bucket_name = "aerocaliper-rag-finops-vjbel"

    client_options = ClientOptions(quota_project_id=project_id)
    parent = f"projects/{project_id}/locations/{location}/collections/default_collection"

    doc_client = discoveryengine_v1.DocumentServiceClient(client_options=client_options)
    import_request = discoveryengine_v1.ImportDocumentsRequest(
        parent=f"{parent}/dataStores/{data_store_id}/branches/0",
        gcs_source=discoveryengine_v1.GcsSource(
            input_uris=[f"gs://{bucket_name}/*"],
            data_schema="custom"
        ),
        reconciliation_mode=discoveryengine_v1.ImportDocumentsRequest.ReconciliationMode.INCREMENTAL
    )
    
    print("Importing FinOps documents...")
    try:
        operation = doc_client.import_documents(request=import_request)
        operation.result()
        print("FinOps import successfully initiated!")
    except Exception as e:
        print("FinOps import failed:", e)

if __name__ == "__main__":
    import_finops()
