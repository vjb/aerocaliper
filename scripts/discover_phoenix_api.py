"""Discover Phoenix Client SDK prompts API."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

from phoenix.client import Client

space_name = os.getenv("ARIZE_SPACE_NAME", "")
base_url = f"https://app.phoenix.arize.com/s/{space_name}" if space_name else "https://app.phoenix.arize.com"
api_key = os.getenv("PHOENIX_API_KEY", "").strip()

client = Client(base_url=base_url, api_key=api_key)

# Inspect the prompts object
print("=== Prompts object type:", type(client.prompts))
print("=== Prompts dir:", [x for x in dir(client.prompts) if not x.startswith('_')])

# Check create signature
import inspect
try:
    sig = inspect.signature(client.prompts.create)
    print("=== prompts.create signature:", sig)
except Exception as e:
    print(f"=== prompts.create error: {e}")

# Try to get an existing prompt
try:
    prompt = client.prompts.get(prompt_identifier="aerocaliperfinopsroutingagent")
    print("=== Got existing prompt:", type(prompt))
    print("=== Prompt dir:", [x for x in dir(prompt) if not x.startswith('_')])
    if hasattr(prompt, '_template'):
        print("=== _template:", prompt._template)
except Exception as e:
    print(f"=== Get prompt error: {e}")
