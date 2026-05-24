import requests
import json
import time

def test_stream(policy):
    print(f"\n--- Testing SSE stream for policy: {policy} ---")
    url = f"http://127.0.0.1:8080/remediate/stream?policy={policy}"
    headers = {"x-api-key": "fake-key"} if False else {} # If needed, we don't have AEROCALIPER_API_KEY set
    
    session = requests.Session()
    response = session.post(url, headers=headers, stream=True)
    
    if response.status_code != 200:
        print(f"Failed to connect: {response.status_code} {response.text}")
        return False
        
    expected_events = ["anomaly_scan", "thought_signature", "backtest_metrics", "candidate_prompt", "patch_deployed"]
    received_events = []
    
    session_id = None
    
    for line in response.iter_lines():
        if not line:
            continue
            
        decoded_line = line.decode('utf-8')
        if decoded_line.startswith("data: "):
            data_str = decoded_line[6:]
            if data_str == "__DONE__":
                break
                
            try:
                event_data = json.loads(data_str)
                event_type = event_data.get("type")
                
                if event_type == "session_start":
                    session_id = event_data.get("session_id")
                    print(f"Session started: {session_id}")
                elif event_type in expected_events:
                    print(f"Received expected event: {event_type}")
                    received_events.append(event_type)
                    
                    if event_type == "backtest_metrics":
                        passed_cases = event_data.get("passed_cases", 0)
                        total_cases = event_data.get("total_cases", 0)
                        print(f"Backtest metrics: {passed_cases}/{total_cases} passed")
                        if policy == "finops":
                            assert total_cases == 6, f"FinOps should have 6 cases, got {total_cases}"
                        else:
                            assert total_cases == 4, f"HR should have 4 cases, got {total_cases}"
                            
                    elif event_type == "candidate_prompt":
                        print(f"Pipeline paused at candidate_prompt. Approving session {session_id}...")
                        # Approve it
                        approve_url = f"http://127.0.0.1:8080/remediate/approve/{session_id}"
                        approve_resp = requests.post(approve_url)
                        print(f"Approve response: {approve_resp.status_code} {approve_resp.text}")
                        
                elif event_type == "error":
                    print(f"Error in stream: {event_data.get('message')}")
                    return False
            except json.JSONDecodeError:
                pass
                
    # Check if all expected events fired in order
    assert [e for e in received_events if e in expected_events] == expected_events, f"Events out of order or missing. Expected {expected_events}, got {received_events}"
    print(f"--- SUCCESS: SSE stream for policy {policy} passed ---")
    return True

if __name__ == "__main__":
    if not test_stream("finops"):
        print("FinOps test failed.")
        exit(1)
    if not test_stream("hr"):
        print("HR test failed.")
        exit(1)
    print("ALL TESTS PASSED.")
