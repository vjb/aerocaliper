import os
from google.cloud import modelarmor_v1
from google.api_core.client_options import ClientOptions

def create_armor():
    project_id = "aerocaliper"
    location = "us-central1"
    template_id = "aerocaliper-armor"
    client_options = ClientOptions(api_endpoint=f"modelarmor.{location}.rep.googleapis.com")
    client = modelarmor_v1.ModelArmorClient(client_options=client_options)
    
    parent = f"projects/{project_id}/locations/{location}"
    print(f"Creating Model Armor template in: {parent}")
    
    template = modelarmor_v1.Template()
    # Simple block-none template just to exist and test the API
    template.filter_config = modelarmor_v1.FilterConfig()
    
    request = modelarmor_v1.CreateTemplateRequest(
        parent=parent,
        template_id=template_id,
        template=template
    )
    
    try:
        response = client.create_template(request=request)
        print("Created template:", response.name)
    except Exception as e:
        print("Failed to create template:", e)

if __name__ == "__main__":
    create_armor()
