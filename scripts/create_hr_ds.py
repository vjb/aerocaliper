import os
from google.cloud import discoveryengine_v1
from google.api_core.client_options import ClientOptions

def create_and_import():
    project_id = "aerocaliper"
    location = "global"
    data_store_id = "hr-ds"
    bucket_name = "aerocaliper-rag-hr-vjbel"

    # Set quota project explicitly in case of billing issues
    client_options = ClientOptions(quota_project_id=project_id)
    ds_client = discoveryengine_v1.DataStoreServiceClient(client_options=client_options)

    parent = f"projects/{project_id}/locations/{location}/collections/default_collection"

    # Create DataStore
    data_store = discoveryengine_v1.DataStore(
        display_name="HR Privacy Data Store",
        industry_vertical=discoveryengine_v1.IndustryVertical.GENERIC,
        solution_types=[discoveryengine_v1.SolutionType.SOLUTION_TYPE_SEARCH],
        content_config=discoveryengine_v1.DataStore.ContentConfig.CONTENT_REQUIRED,
    )

    request = discoveryengine_v1.CreateDataStoreRequest(
        parent=parent,
        data_store=data_store,
        data_store_id=data_store_id,
    )

    print("Creating DataStore...")
    try:
        operation = ds_client.create_data_store(request=request)
        response = operation.result()
        print("Created DataStore:", response.name)
    except Exception as e:
        print("DataStore creation failed (may already exist):", e)

    # Import Documents
    doc_client = discoveryengine_v1.DocumentServiceClient(client_options=client_options)
    import_request = discoveryengine_v1.ImportDocumentsRequest(
        parent=f"{parent}/dataStores/{data_store_id}/branches/0",
        gcs_source=discoveryengine_v1.GcsSource(
            input_uris=[f"gs://{bucket_name}/*"],
            data_schema="custom"
        ),
        reconciliation_mode=discoveryengine_v1.ImportDocumentsRequest.ReconciliationMode.INCREMENTAL
    )
    
    print("Importing documents...")
    try:
        operation = doc_client.import_documents(request=import_request)
        operation.result()
        print("Import successfully initiated!")
    except Exception as e:
        print("Import failed:", e)

if __name__ == "__main__":
    create_and_import()
