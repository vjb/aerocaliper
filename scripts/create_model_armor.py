import os
import sys
from google.api_core.client_options import ClientOptions
from google.cloud import modelarmor_v1
from dotenv import load_dotenv

load_dotenv()

project_id = os.getenv("GOOGLE_CLOUD_PROJECT", "aerocaliper")
location_id = os.getenv("MODEL_ARMOR_LOCATION", "us-central1")
template_id = "aerocaliper-policy"
parent = f"projects/{project_id}/locations/{location_id}"

print(f"Creating Model Armor Template '{template_id}' in {parent}...")

client = modelarmor_v1.ModelArmorClient(
    transport="rest",
    client_options=ClientOptions(
        api_endpoint=f"modelarmor.{location_id}.rep.googleapis.com"
    ),
)

template_config = modelarmor_v1.Template(
    filter_config=modelarmor_v1.FilterConfig(
        # Use valid attributes based on the error output: PiAndJailbreakFilterSettings
        pi_and_jailbreak_filter_settings=modelarmor_v1.PiAndJailbreakFilterSettings(
            jailbreak_filter_settings=modelarmor_v1.JailbreakFilterSettings(
                filter_enforcement=modelarmor_v1.FilterEnforcement.ENABLED
            ),
            pi_filter_settings=modelarmor_v1.PiFilterSettings(
                filter_enforcement=modelarmor_v1.FilterEnforcement.ENABLED
            )
        )
    )
)

request = modelarmor_v1.CreateTemplateRequest(
    parent=parent,
    template_id=template_id,
    template=template_config
)

try:
    response = client.create_template(request=request)
    print(f"Template created successfully: {response.name}")
except Exception as e:
    print(f"Failed to create template: {e}")
