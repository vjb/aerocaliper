import os
import google.genai
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("GOOGLE_AGENT_PLATFORM_API_KEY")

# As per the new Agent Platform documentation
client = google.genai.Client(
    vertexai=True, 
    api_key=api_key
)

response = client.models.generate_content(
    model="gemini-3.1-pro-preview",
    contents="Explain how AI works in 5 words."
)

print(response.text)
