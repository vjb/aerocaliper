# AeroCaliper: Test-Driven Task Breakdown

This document outlines the granular, test-driven development (TDD) phases required to build AeroCaliper. Each phase must pass its automated test suite before progressing.

## Phase 1: Environment & Mock Target Agent
**Goal:** Scaffold the Python environment and simulate the "Confused Deputy" hallucination.
- [ ] Initialize Python virtual environment (`venv`) and install dependencies (`pytest`, `google-cloud-aiplatform`, `arize-phoenix-otel`).
- [ ] Create `target_agent.py`. Define a simple mock agent function that accepts a user prompt and outputs a JSON deployment payload.
- [ ] **Test (`test_target_agent.py`):** Write a test ensuring that when prompted with "Deploy to the biggest cluster", the agent outputs `{"target_cluster": "X5-48TB"}` without a `budget_tag`.

## Phase 2: Arize Phoenix Instrumentation & Evaluators
**Goal:** Instrument the Target Agent and write the FinOps Code Evaluator.
- [ ] Wrap `target_agent.py` with OpenTelemetry auto-instrumentation pointing to the Arize Phoenix local/cloud instance.
- [ ] Create `evaluators.py`. Write a deterministic code evaluator (`@create_evaluator(kind="code")`) that checks for the `X5-48TB` string and the `budget_tag: approved` string.
- [ ] **Test (`test_evaluators.py`):** Feed a mock trace (from Phase 1) into the evaluator function. Assert that the evaluator correctly returns `FAILED` and tags it as a `FinOps Violation`.

## Phase 3: The AeroCaliper MCP Client (Core Logic)
**Goal:** Build the remediation agent that connects to the Arize MCP server and uses Gemini 3.1 Pro.
- [ ] Create `aerocaliper.py`. Set up the Google Cloud ADK application.
- [ ] Implement the MCP client connection to the Arize server. Add functions to call `get-spans` and `upsert-prompt`.
- [ ] Implement the `Interactions API` logic. Ensure the `thought_signature` token from the diagnostic phase is captured and passed into the `run_experiment` background poll.
- [ ] **Test (`test_aerocaliper.py`):** Mock the MCP server responses. Assert that AeroCaliper successfully initiates a background job, polls until `status == 'completed'`, and generates a patched system prompt.

## Phase 4: Security (Agent Gateway & Model Armor)
**Goal:** Secure the egress traffic from AeroCaliper to Arize.
- [ ] Create `infra/gateway_config.yaml`. Define the Agent Gateway egress routing rules.
- [ ] Create `infra/model_armor_policy.yaml`. Define the deep packet inspection rules (e.g., blocking SQL injection or prompt injection patterns in outbound traffic).
- [ ] **Test (`test_security.py`):** Write an integration test that attempts to send a malicious payload through the local gateway simulator. Assert that a `403 Forbidden` is returned.

## Phase 5: End-to-End Orchestration & Recording
**Goal:** Run the entire pipeline autonomously and record the video submission.
- [ ] Create `dockerfile` and `cloudbuild.yaml` for deployment.
- [ ] Deploy AeroCaliper to Cloud Run.
- [ ] Trigger the hallucination in the Target Agent -> Watch Arize flag it -> Watch AeroCaliper pull the trace, calibrate, experiment, and push the fix -> Verify the Target Agent now requires budget approval.
- [ ] **Test:** The final 3-minute hackathon demo recording.
