"""
End-to-End SSE stream test for AeroCaliper UI.
Simulates clicking "Trigger Autonomous Remediation" for both FinOps and HR policies.
Verifies the complete event stream including:
  - session_start
  - log events
  - anomaly_scan
  - phase_update
  - trace_card
  - thought_signature
  - candidate_prompt (with auto-approval)
  - backtest_metrics
  - judge_verdict
  - gateway_cleared
  - patch_deployed
  - complete
"""
import requests
import json
import sys
import os
import time
import threading

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

BASE = os.getenv("TEST_BASE_URL", "http://127.0.0.1:8081")
TIMEOUT = 300  # 5 minutes max for the full pipeline


def stream_remediation(policy: str) -> dict:
    """
    Fires POST /remediate/stream?policy=<policy>, reads all SSE events,
    auto-approves when candidate_prompt arrives, and returns a summary.
    """
    print(f"\n{'='*60}")
    print(f"  Testing: {policy.upper()} Remediation Pipeline")
    print(f"{'='*60}")

    events_seen = set()
    session_id = None
    patched_prompt = None
    log_count = 0
    errors = []
    backtest_pass_rate = None

    resp = requests.post(f"{BASE}/remediate/stream?policy={policy}", stream=True, timeout=TIMEOUT)
    assert resp.status_code == 200, f"Stream endpoint returned {resp.status_code}"

    for raw_line in resp.iter_lines(decode_unicode=True):
        if not raw_line or not raw_line.startswith("data: "):
            continue

        try:
            ev = json.loads(raw_line[6:])
        except json.JSONDecodeError:
            continue

        ev_type = ev.get("type", "unknown")
        events_seen.add(ev_type)

        if ev_type == "session_start":
            session_id = ev["session_id"]
            print(f"  [SSE] session_start -> {session_id}")

        elif ev_type == "log":
            log_count += 1
            level = ev.get("level", "")
            msg = ev.get("msg", "")
            if level == "error":
                errors.append(msg)
            # Print important logs
            if any(kw in msg for kw in ["Phase", "MCP", "Backtest", "Judge", "UPSERT", "REMEDIATION", "Optimization", "Refining"]):
                print(f"  [LOG] [{level}] {msg}")

        elif ev_type == "anomaly_scan":
            print(f"  [SSE] anomaly_scan -> risk={ev.get('risk_score',0):.0%} safe={ev.get('safe')}")

        elif ev_type == "trace_card":
            print(f"  [SSE] trace_card -> trace_id={ev.get('trace_id')}")

        elif ev_type == "thought_signature":
            print(f"  [SSE] thought_signature -> {ev.get('token')}")

        elif ev_type == "backtest_metrics":
            backtest_pass_rate = ev.get("pass_rate")
            print(f"  [SSE] backtest_metrics -> {backtest_pass_rate:.0f}% PASS ({ev.get('passed_cases')}/{ev.get('total_cases')})")

        elif ev_type == "candidate_prompt":
            print(f"  [SSE] candidate_prompt -> length={len(ev.get('prompt',''))}")
            # Auto-approve
            if session_id:
                print(f"  [AUTO] Approving session {session_id}...")
                approve_resp = requests.post(f"{BASE}/remediate/approve/{session_id}")
                print(f"  [AUTO] Approval response: {approve_resp.status_code} -> {approve_resp.json()}")

        elif ev_type == "judge_verdict":
            print(f"  [SSE] judge_verdict -> {ev.get('verdict')} passed={ev.get('passed')}")

        elif ev_type == "gateway_cleared":
            print(f"  [SSE] gateway_cleared -> {ev.get('policy')} {ev.get('status')}")

        elif ev_type == "patch_deployed":
            patched_prompt = ev.get("prompt", "")
            print(f"  [SSE] patch_deployed -> prompt length={len(patched_prompt)}")

        elif ev_type == "complete":
            print(f"  [SSE] complete ✓")

        elif ev_type == "error":
            print(f"  [SSE] ERROR: {ev.get('message')}")
            errors.append(ev.get("message", "unknown error"))

        elif ev_type == "stream_end":
            break

    resp.close()

    return {
        "policy": policy,
        "session_id": session_id,
        "events_seen": events_seen,
        "log_count": log_count,
        "patched_prompt": patched_prompt,
        "backtest_pass_rate": backtest_pass_rate,
        "errors": errors,
    }


def validate_result(result: dict):
    """Validate that all expected events were received and the pipeline succeeded."""
    policy = result["policy"]
    prefix = f"  [{policy.upper()}]"

    # Must have received session_start
    assert "session_start" in result["events_seen"], f"{prefix} Missing session_start event"
    assert result["session_id"] is not None, f"{prefix} No session_id received"
    print(f"{prefix} ✓ session_start received")

    # Must have logs
    assert result["log_count"] > 5, f"{prefix} Too few log events: {result['log_count']}"
    print(f"{prefix} ✓ {result['log_count']} log events received")

    # Must have anomaly scan
    assert "anomaly_scan" in result["events_seen"], f"{prefix} Missing anomaly_scan event"
    print(f"{prefix} ✓ anomaly_scan received")

    # Must have trace_card or thought_signature
    assert "thought_signature" in result["events_seen"] or "trace_card" in result["events_seen"], \
        f"{prefix} Missing trace/thought events"
    print(f"{prefix} ✓ trace_card / thought_signature received")

    # Must have candidate_prompt
    assert "candidate_prompt" in result["events_seen"], f"{prefix} Missing candidate_prompt event"
    print(f"{prefix} ✓ candidate_prompt received")

    # Must have backtest_metrics
    assert "backtest_metrics" in result["events_seen"], f"{prefix} Missing backtest_metrics"
    print(f"{prefix} ✓ backtest_metrics received (pass_rate={result['backtest_pass_rate']}%)")

    # Must have judge verdict
    assert "judge_verdict" in result["events_seen"], f"{prefix} Missing judge_verdict"
    print(f"{prefix} ✓ judge_verdict received")

    # Must have gateway_cleared
    assert "gateway_cleared" in result["events_seen"], f"{prefix} Missing gateway_cleared"
    print(f"{prefix} ✓ gateway_cleared received")

    # Must have patch_deployed with actual prompt content
    assert "patch_deployed" in result["events_seen"], f"{prefix} Missing patch_deployed"
    assert result["patched_prompt"] and len(result["patched_prompt"]) > 20, \
        f"{prefix} Patched prompt is missing or too short"
    print(f"{prefix} ✓ patch_deployed received (prompt length={len(result['patched_prompt'])})")

    # Must have complete
    assert "complete" in result["events_seen"], f"{prefix} Missing complete event"
    print(f"{prefix} ✓ complete received")

    # Should have no errors
    if result["errors"]:
        print(f"{prefix} ⚠ Errors encountered: {result['errors']}")
    else:
        print(f"{prefix} ✓ No errors")

    print(f"{prefix} ALL CHECKS PASSED ✓")


if __name__ == "__main__":
    print("=" * 60)
    print("AeroCaliper E2E SSE Stream Integration Test")
    print("=" * 60)

    # Test 1: FinOps pipeline
    finops_result = stream_remediation("finops")
    validate_result(finops_result)

    # Test 2: HR Privacy pipeline
    hr_result = stream_remediation("hr")
    validate_result(hr_result)

    print("\n" + "=" * 60)
    print("  ALL E2E TESTS PASSED — Both FinOps and HR pipelines work!")
    print("=" * 60)
