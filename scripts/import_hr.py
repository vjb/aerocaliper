import os
from google.cloud import storage
from google.cloud import discoveryengine_v1

def upload_and_import():
    project_id = "aerocaliper"
    bucket_name = "aerocaliper-finops-rag-vjbel"
    
    # Upload to GCS
    client = storage.Client(project=project_id)
    bucket = client.bucket(bucket_name)
    blob = bucket.blob("HR_Privacy_Policy_2026.txt")
    blob.upload_from_filename("HR_Privacy_Policy_2026.txt")
    print("Uploaded to GCS.")

    # Trigger Import to Datastore
    ds_client = discoveryengine_v1.DocumentServiceClient()
    parent = f"projects/622472185650/locations/global/collections/default_collection/dataStores/finops-ds/branches/0"
    
    request = discoveryengine_v1.ImportDocumentsRequest(
        parent=parent,
        gcs_source=discoveryengine_v1.GcsSource(
            input_uris=[f"gs://{bucket_name}/HR_Privacy_Policy_2026.txt"],
            data_schema="custom"
        ),
        reconciliation_mode=discoveryengine_v1.ImportDocumentsRequest.ReconciliationMode.INCREMENTAL
    )
    
    print("Starting import...")
    try:
        operation = ds_client.import_documents(request=request)
        print("Waiting for operation to complete...")
        response = operation.result()
        print("Import completed:", response)
    except Exception as e:
        print("Import failed:", e)

if __name__ == "__main__":
    upload_and_import()
