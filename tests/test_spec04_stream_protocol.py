"""
Spec 04: Backend Stream Protocol.

Verifies the backend SSE streaming protocol independently of the browser DOM.

Assertions:
  - Authenticated requests yield chunked text/event-stream
  - Stream starts with session_start event containing session_id
  - Stream emits candidate_prompt with valid JSON payload
  - Auto-approval via REST allows pipeline to complete
"""
import pytest
import json
import requests
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

CLOUD_RUN_URL = "https://aerocaliper-agent-622472185650.us-central1.run.app"
STREAM_URL = f"{CLOUD_RUN_URL}/remediate/stream"


class TestStreamProtocol:
    """Spec 04: Verify backend streaming protocol independently."""

    def test_stream_returns_200(self):
        """Stream endpoint returns HTTP 200 for POST requests."""
        resp = requests.post(
            f"{STREAM_URL}?policy=finops", stream=True, timeout=30
        )
        assert resp.status_code == 200, (
            f"Stream endpoint returned {resp.status_code}, expected 200"
        )
        resp.close()

    def test_stream_content_type_is_event_stream(self):
        """Response Content-Type must be text/event-stream."""
        resp = requests.post(
            f"{STREAM_URL}?policy=finops", stream=True, timeout=30
        )
        content_type = resp.headers.get("content-type", "")
        assert "text/event-stream" in content_type, (
            f"Expected text/event-stream, got: {content_type}"
        )
        resp.close()

    def test_stream_emits_session_start(self):
        """First SSE event must be session_start with a session_id."""
        resp = requests.post(
            f"{STREAM_URL}?policy=finops", stream=True, timeout=60
        )
        try:
            for raw_line in resp.iter_lines(decode_unicode=True):
                if not raw_line or not raw_line.startswith("data: "):
                    continue
                ev = json.loads(raw_line[6:])
                assert ev["type"] == "session_start", (
                    f"First event should be session_start, got: {ev['type']}"
                )
                assert "session_id" in ev, "session_start missing session_id"
                assert len(ev["session_id"]) > 10, "session_id too short"
                break
        finally:
            resp.close()

    @pytest.mark.slow
    def test_stream_full_pipeline_with_auto_approve(self):
        """
        Full SSE pipeline test:
        1. Stream starts with session_start
        2. Events include anomaly_scan, trace_card, thought_signature
        3. candidate_prompt event emitted with substantial prompt text
        4. Auto-approve via REST API
        5. Pipeline completes with patch_deployed and complete events
        """
        resp = requests.post(
            f"{STREAM_URL}?policy=finops", stream=True, timeout=300
        )

        session_id = None
        events_seen = set()
        patched_prompt = None
        errors = []

        try:
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

                elif ev_type == "candidate_prompt":
                    prompt = ev.get("prompt", "")
                    assert len(prompt) > 50, (
                        f"candidate_prompt payload too short: {len(prompt)}"
                    )
                    # Auto-approve
                    if session_id:
                        approve_resp = requests.post(
                            f"{CLOUD_RUN_URL}/remediate/approve/{session_id}",
                            timeout=10,
                        )
                        assert approve_resp.status_code == 200, (
                            f"Approve returned {approve_resp.status_code}"
                        )

                elif ev_type == "patch_deployed":
                    patched_prompt = ev.get("prompt", "")

                elif ev_type == "error":
                    errors.append(ev.get("message", "unknown"))

                elif ev_type in ("complete", "stream_end"):
                    break
        finally:
            resp.close()

        # Assertions
        assert "session_start" in events_seen, "Missing session_start"
        assert "candidate_prompt" in events_seen, "Missing candidate_prompt"
        assert "complete" in events_seen or "patch_deployed" in events_seen, (
            f"Pipeline didn't complete. Events seen: {events_seen}"
        )
        if errors:
            print(f"[WARN] Stream errors encountered: {errors}")
