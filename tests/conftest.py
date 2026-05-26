"""
AeroCaliper E2E Test Suite — Shared Fixtures & Configuration.

Provides session-scoped fixtures for:
  - Baseline state management (Arize Prompt Registry reset/teardown)
  - Playwright browser context lifecycle
  - Cloud Run page navigation
  - Target agent subprocess runner
"""
import pytest
import os
import sys
import subprocess

# Allow imports from the project root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# ─────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────
CLOUD_RUN_URL = "https://aerocaliper-agent-622472185650.us-central1.run.app"
PHOENIX_URL = "https://app.phoenix.arize.com"
PYTHON_CMD = ["py", "-3.13"]
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
ARTIFACTS_DIR = os.path.join(PROJECT_ROOT, "tests", "artifacts")

os.makedirs(ARTIFACTS_DIR, exist_ok=True)


# ─────────────────────────────────────────────────────────────
# Helper: run target_agent.py as a subprocess
# ─────────────────────────────────────────────────────────────
def run_target_agent(use_case: str, mode: str, timeout: int = 180) -> str:
    """
    Execute target_agent.py with the given use-case and mode.
    Returns the combined stdout+stderr as a string.
    """
    cmd = [*PYTHON_CMD, "target_agent.py", "--use-case", use_case, "--mode", mode]
    result = subprocess.run(
        cmd,
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    return result.stdout + result.stderr


def _run_reset_registry():
    """Execute scripts/reset_registry.py to reset all prompts to vulnerable baseline."""
    cmd = [*PYTHON_CMD, os.path.join("scripts", "reset_registry.py")]
    result = subprocess.run(
        cmd,
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        timeout=120,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"reset_registry.py failed (exit {result.returncode}):\n{result.stderr}\n{result.stdout}"
        )
    print(result.stdout)


# ─────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────
@pytest.fixture(scope="session")
def baseline_state():
    """
    Session-scoped fixture: resets both prompts to vulnerable baseline
    BEFORE all tests, then resets again AFTER all tests to leave the
    environment demo-ready.
    """
    print("\n[SETUP] Resetting Arize Prompt Registry to State:Baseline...")
    _run_reset_registry()
    yield
    print("\n[TEARDOWN] Resetting Arize Prompt Registry to State:Baseline...")
    _run_reset_registry()


@pytest.fixture(scope="session")
def browser_context():
    """
    Session-scoped fixture: launches a Playwright Chromium browser.
    Closes it on teardown.
    """
    from playwright.sync_api import sync_playwright

    pw = sync_playwright().start()
    browser = pw.chromium.launch(headless=True)
    context = browser.new_context(viewport={"width": 1400, "height": 900})
    yield context
    context.close()
    browser.close()
    pw.stop()


@pytest.fixture
def cloud_run_page(browser_context):
    """
    Per-test fixture: creates a fresh page navigated to the Cloud Run UI.
    Closes the page on teardown.
    """
    page = browser_context.new_page()
    page.goto(CLOUD_RUN_URL, wait_until="domcontentloaded")
    page.wait_for_timeout(3000)  # Allow fonts + JS to load
    yield page
    page.close()
