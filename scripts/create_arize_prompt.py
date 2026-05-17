import os
from dotenv import load_dotenv
from phoenix.client import Client
import sys

load_dotenv()

def create_prompt():
    print("Creating Arize Prompt...")
    try:
        client = Client()
        template = "You are an internal enterprise routing agent. Route workloads based on the user request. Available clusters: e2-micro, h200-megagpu-8g, gb200-blackwell-supercluster. For batch processing, training, or experiments, you must optimize costs by using spot instances."
        
        # In Phoenix client, we can create or update a prompt
        # We will try to create or push a version
        try:
            # Let's see if client.prompts.create exists, or just push a version
            prompt = client.create_prompt(
                name="aerocaliper-finops-routing-agent",
                template=template
            )
            print(f"PASS: Prompt created/updated: {prompt}")
        except Exception as e:
            print(f"FAIL: {e}")
            sys.exit(1)
            
    except Exception as e:
        print(f"Initialization FAIL: {e}")
        sys.exit(1)

if __name__ == "__main__":
    create_prompt()
