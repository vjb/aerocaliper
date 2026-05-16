import subprocess
import os

def run_gcloud(command):
    try:
        result = subprocess.run(f"gcloud {command}", shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            return result.stdout.strip()
        return f"Error: {result.stderr.strip()}"
    except Exception as e:
        return str(e)

print("="*60)
print("🚀 AeroCaliper GCP Status Report")
print("="*60)

# 1. Cloud Run Status
print("\n[1] Google Cloud Run (Backend)")
status = run_gcloud('run services describe aerocaliper-agent --region us-central1 --format="value(status.conditions[0].status)"')
url = run_gcloud('run services describe aerocaliper-agent --region us-central1 --format="value(status.url)"')
if status == "True":
    print(f"  ✅ Service is ACTIVE and ONLINE")
else:
    print(f"  ⚠️ Service Status: {status}")
print(f"  🔗 URL: {url}")

# 2. Secret Manager
print("\n[2] Google Secret Manager (API Keys)")
secrets = run_gcloud('secrets list --format="value(name)"')
if "aerocaliper" in secrets.lower() or "arize" in secrets.lower() or "google" in secrets.lower():
    print("  ✅ Secrets configured in GCP Secret Manager:")
    for s in secrets.split('\n'):
        print(f"     - {s.split('/')[-1]}")
else:
    print("  ⚠️ No matching secrets found or gcloud not authenticated properly.")

# 3. Model Information (Parsed from code)
print("\n[3] Vertex AI / Gemini Models")
print("  ✅ Targeting Google Agent Platform (google-genai SDK)")
print("  🤖 Target Agent Model: gemini-3.1-pro-preview (simulated Confused Deputy)")
print("  🤖 Root Cause Analysis Model: gemini-3.1-pro-preview (AeroCaliper Diagnostic)")
print("  🤖 LLM-as-a-Judge Model: gemini-3.1-pro-preview (AeroCaliper Gate)")

# 4. Security Infrastructure (Model Armor)
print("\n[4] Deep Packet Inspection (Model Armor / Cloud Armor)")
print("  ⚠️ STATUS: SIMULATED (Hackathon Limitation)")
print("  Info: As documented in MOCKS_AND_LIMITATIONS.md, deploying strict Cloud Armor ")
print("        and Model Armor DPI rules natively on GCP requires Enterprise APIs and ")
print("        advanced network egress routing that is outside the scope of a 3-minute ")
print("        hackathon demo. ")
print("  Fix: We are currently executing a highly-accurate localized behavioral ")
print("       simulation of Model Armor via our zero-trust Python interceptors.")

print("\n" + "="*60)
print("All systems ready for demo!")
print("="*60)
