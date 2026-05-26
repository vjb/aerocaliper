"""Quick import test for stress test dependencies."""
try:
    from phoenix.client import Client
    print("phoenix.client OK")
except ImportError as e:
    print(f"phoenix.client FAIL: {e}")

try:
    import google.genai
    print("google.genai OK")
except ImportError as e:
    print(f"google.genai FAIL: {e}")

try:
    from openinference.instrumentation.google_genai import GoogleGenAIInstrumentor
    print("openinference OK")
except ImportError as e:
    print(f"openinference FAIL: {e}")

try:
    from phoenix.otel import register
    print("phoenix.otel OK")
except ImportError as e:
    print(f"phoenix.otel FAIL: {e}")

print("All import checks done.")
