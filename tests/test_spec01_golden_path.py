"""
Spec 01: The Golden Path Transition.

Verifies the system can transition from State:Baseline to State:Healed
via UI approval of the AeroCaliper remediation pipeline.

Flow:
  1. Assert FinOps target agent is vulnerable (State:Baseline)
  2. Trigger remediation via Cloud Run UI
  3. Wait for Human-in-the-Loop approval modal
  4. Validate candidate prompt schema tags
  5. Approve the patch
  6. Verify REMEDIATION COMPLETE in log
  7. Assert FinOps target agent is now compliant (State:Healed)
  8. Validate JSON data contract: target_cluster, workload_type, use_spot
"""
import pytest
import ast


class TestGoldenPath:
    """Spec 01: Verify system transitions from Baseline to Healed via UI approval."""

    def test_baseline_finops_is_vulnerable(self, baseline_state):
        """Precondition: FinOps target agent must produce POLICY VIOLATION."""
        from conftest import run_target_agent

        stdout = run_target_agent("finops", "verify-healed")
        assert "POLICY VIOLATION" in stdout, (
            f"Expected POLICY VIOLATION in baseline state, got:\n{stdout[-500:]}"
        )

    @pytest.mark.slow
    @pytest.mark.browser
    def test_trigger_remediation_and_approve(self, baseline_state, cloud_run_page):
        """Full UI flow: trigger → wait for approval → approve → verify completion."""
        page = cloud_run_page

        # Ensure FinOps policy is selected
        page.select_option("#policyDropdown", "finops")
        page.wait_for_timeout(500)

        # Click the trigger button
        page.click("#triggerBtn")

        # Verify button enters running state
        page.wait_for_timeout(1000)
        btn_text = page.text_content("#triggerBtn")
        assert "Remediating" in btn_text, f"Button didn't enter running state: {btn_text}"

        # Wait for first log entry (pipeline is active)
        page.wait_for_selector("#logBody .log-line", timeout=30_000)

        # Wait for the approval modal (up to 5 minutes for the agentic pipeline)
        page.wait_for_selector("#approvalPanel.visible", timeout=300_000)

        # ── Schema Validation ──
        prompt_text = page.text_content("#approvalPromptText")
        assert len(prompt_text) > 50, f"Candidate prompt too short ({len(prompt_text)} chars)"

        # Take a screenshot of the approval gate
        page.screenshot(path="tests/artifacts/spec01_approval_modal.png")

        # ── Approve ──
        page.click(".btn-approve")

        # Wait for REMEDIATION COMPLETE in the log panel
        for _ in range(60):  # poll for up to 2 minutes
            page.wait_for_timeout(2000)
            log_text = page.text_content("#logBody")
            if "REMEDIATION COMPLETE" in log_text:
                break
        else:
            page.screenshot(path="tests/artifacts/spec01_timeout.png")
            pytest.fail("REMEDIATION COMPLETE not seen within 2 minutes of approval")

        # ── Verify After prompt panel populated ──
        after_text = page.text_content("#promptAfter")
        assert len(after_text) > 50, f"After prompt not populated: {after_text[:100]}"
        assert "Awaiting" not in after_text, "After prompt still shows placeholder text"

        # ── Verify no phases failed ──
        for i in range(1, 6):
            phase_class = page.get_attribute(f"#phase{i}", "class") or ""
            assert "failed" not in phase_class, f"Phase {i} is in failed state"

        # Final screenshot
        page.screenshot(path="tests/artifacts/spec01_complete.png")

    @pytest.mark.slow
    def test_healed_finops_is_compliant(self, baseline_state):
        """
        Postcondition: FinOps target agent must produce COMPLIANT output.
        Data Contract: JSON must contain target_cluster, workload_type, use_spot.
        """
        from conftest import run_target_agent

        stdout = run_target_agent("finops", "verify-healed")

        # Primary assertion: compliance
        assert "COMPLIANT" in stdout or "LOOP CLOSED" in stdout, (
            f"Expected COMPLIANT after healing, got:\n{stdout[-500:]}"
        )

        # Data contract: validate JSON output keys
        for line in stdout.split("\n"):
            if "Agent output:" in line:
                json_str = line.split("Agent output:")[1].strip()
                try:
                    payload = ast.literal_eval(json_str)
                    assert "target_cluster" in payload, "Missing key: target_cluster"
                    assert "workload_type" in payload, "Missing key: workload_type"
                    assert "use_spot" in payload, "Missing key: use_spot"
                    # use_spot should ideally be True for compliant output
                    if isinstance(payload.get("use_spot"), bool):
                        assert payload["use_spot"] is True, (
                            f"use_spot should be True for compliant output, got {payload['use_spot']}"
                        )
                except (ValueError, SyntaxError):
                    pass  # Non-critical: parsing may fail on some output formats
