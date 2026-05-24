"""Quick smoke test for the AeroCaliper frontend and API endpoints."""
import requests
import time
import sys

BASE = "http://127.0.0.1:8081"

def test_health():
    r = requests.get(f"{BASE}/health")
    assert r.status_code == 200, f"Health check failed: {r.status_code}"
    data = r.json()
    assert data["status"] == "ok"
    assert data["version"] == "3.1.0"
    print(f"[PASS] /health -> {data}")

def test_frontend_loads():
    r = requests.get(f"{BASE}/")
    assert r.status_code == 200, f"Frontend load failed: {r.status_code}"
    html = r.text
    
    # Check all critical element IDs exist in the HTML
    required_ids = [
        'id="traceCount"',
        'id="remTime"',
        'id="backtestLabel"',
        'id="triggerBtn"',
        'id="policyDropdown"',
        'id="backtestPolicyDropdown"',
        'id="approvalPanel"',
        'id="logBody"',
        'id="a2uiCards"',
        'id="promptBefore"',
        'id="promptAfter"',
        'id="approveBtn"',
        'id="timer"',
        'id="sseStatus"',
    ]
    
    missing = [eid for eid in required_ids if eid not in html]
    if missing:
        print(f"[FAIL] Missing HTML element IDs: {missing}")
        sys.exit(1)
    print(f"[PASS] All {len(required_ids)} critical element IDs present in HTML")
    
    # Check JS functions are defined
    required_funcs = [
        'triggerRemediation',
        'approveRemediation',
        'rejectRemediation',
        'updatePolicyDisplay',
        'updateBacktestUI',
        'handleA2UIEvent',
        'escHtml',
    ]
    missing_funcs = [f for f in required_funcs if f not in html]
    if missing_funcs:
        print(f"[FAIL] Missing JS functions: {missing_funcs}")
        sys.exit(1)
    print(f"[PASS] All {len(required_funcs)} JS functions defined in HTML")

def test_remediate_stream_starts():
    """Test that the SSE stream endpoint responds and emits session_start."""
    r = requests.post(f"{BASE}/remediate/stream?policy=finops", stream=True, timeout=15)
    assert r.status_code == 200, f"Stream endpoint failed: {r.status_code}"
    
    # Read the first chunk to verify SSE format
    import json
    for line in r.iter_lines(decode_unicode=True):
        if line and line.startswith("data: "):
            data = json.loads(line[6:])
            assert data["type"] == "session_start", f"Expected session_start, got: {data['type']}"
            assert "session_id" in data, "Missing session_id in session_start"
            print(f"[PASS] /remediate/stream -> session_start with session_id={data['session_id']}")
            r.close()
            return
    
    print("[FAIL] No SSE data received from stream")
    r.close()
    sys.exit(1)

if __name__ == "__main__":
    print("=" * 50)
    print("AeroCaliper Frontend & API Smoke Tests")
    print("=" * 50)
    
    test_health()
    test_frontend_loads()
    test_remediate_stream_starts()
    
    print("=" * 50)
    print("ALL SMOKE TESTS PASSED")
    print("=" * 50)
