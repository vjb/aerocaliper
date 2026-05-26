"""
Spec 02: The Abort Path Transition.

Verifies the system rejects state transitions when HITL approval is denied.

Flow:
  1. Assert HR target agent is vulnerable (State:Baseline)
  2. Trigger HR remediation via Cloud Run UI
  3. Wait for approval modal
  4. Click Reject
  5. Verify "Admin REJECTED" appears in the log
  6. Assert HR target agent is still vulnerable (State:Baseline preserved)
"""
import pytest


class TestAbortPath:
    """Spec 02: Verify system rejects transitions when HITL approval is denied."""

    def test_baseline_hr_is_vulnerable(self, baseline_state):
        """Precondition: HR target agent must produce POLICY VIOLATION."""
        from conftest import run_target_agent

        stdout = run_target_agent("hr", "verify-healed")
        assert "POLICY VIOLATION" in stdout, (
            f"Expected POLICY VIOLATION for HR baseline, got:\n{stdout[-500:]}"
        )

    @pytest.mark.slow
    @pytest.mark.browser
    def test_trigger_and_reject_hr(self, baseline_state, cloud_run_page):
        """UI flow: switch to HR → trigger → wait for approval → reject."""
        page = cloud_run_page

        # Switch to HR policy
        page.select_option("#policyDropdown", "hr")
        page.wait_for_timeout(500)

        # Verify the Before prompt updates to HR content
        before_text = page.text_content("#promptBefore")
        assert "HCM" in before_text or "Human Capital" in before_text, (
            f"Before panel didn't switch to HR: {before_text[:100]}"
        )

        # Click trigger
        page.click("#triggerBtn")

        # Wait for first log entry
        page.wait_for_selector("#logBody .log-line", timeout=30_000)

        # Wait for approval modal (up to 5 minutes)
        page.wait_for_selector("#approvalPanel.visible", timeout=300_000)

        # Take screenshot of the HR approval gate
        page.screenshot(path="tests/artifacts/spec02_hr_approval.png")

        # ── Reject ──
        page.click(".btn-reject")
        page.wait_for_timeout(3000)

        # Verify rejection is reflected in the log
        log_text = page.text_content("#logBody")
        assert "REJECTED" in log_text or "rejected" in log_text.lower(), (
            f"Log doesn't mention rejection:\n{log_text[-300:]}"
        )

        # Verify the modal is dismissed
        panel_class = page.get_attribute("#approvalPanel", "class") or ""
        assert "visible" not in panel_class, "Approval panel still visible after rejection"

        # Final screenshot
        page.screenshot(path="tests/artifacts/spec02_rejected.png")

    @pytest.mark.slow
    def test_hr_still_vulnerable_after_reject(self, baseline_state):
        """Postcondition: HR target agent must still produce POLICY VIOLATION."""
        from conftest import run_target_agent

        stdout = run_target_agent("hr", "verify-healed")
        assert "POLICY VIOLATION" in stdout, (
            "HR should still be vulnerable after rejection, "
            f"but got:\n{stdout[-500:]}"
        )
