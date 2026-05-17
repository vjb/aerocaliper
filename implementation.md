# AeroCaliper: End-to-End Implementation Plan

This document serves as the master blueprint for building, testing, and deploying the AeroCaliper hackathon project. It ensures a highly rigorous, enterprise-grade development process.

## 1. Core Architecture
AeroCaliper is structured as a two-agent ecosystem governed by an observability control plane.
1. **The Target Agent (Vulnerable):** A standard Google Cloud Vertex AI agent tasked with deploying infrastructure. It is initially vulnerable to a "confused deputy" hallucination.
2. **Arize Phoenix (The Control Plane):** Instruments the Target Agent via OpenTelemetry. It uses programmatic code evaluators to score the agent's actions.
3. **AeroCaliper (The Remediation Agent):** An ADK-built Python application running on Cloud Run. It is triggered by Arize, connects via MCP, and uses Gemini 3.1 Pro to patch the Target Agent.

## 2. Budget Control Mechanism (The Use Case)
To demonstrate undeniable ROI for the hackathon, we will build a **FinOps Budget Violation** scenario.
* **The Vulnerability:** The Target Agent's system prompt allows it to route workloads. If prompted maliciously or poorly, it might select the expensive `c3-standard-88` cluster without verifying budget approval.
* **The Detection (Evaluator):** We will write a deterministic Arize Code Evaluator in Python. It scans the OTel trace. If the trace contains the payload `"target_cluster": "c3-standard-88"` but lacks `"budget_tag": "approved"`, it flags the trace as `FAILED`.
* **The Remediation:** AeroCaliper must rewrite the Target Agent's prompt to explicitly enforce: *"Before deploying to c3-standard clusters, you must append the 'budget_tag: approved' parameter."*

## 3. Test-Driven Development (TDD) Strategy
To ensure a robust, "vetted" implementation, every component will be built with automated testing. We will use `pytest`.
* **Unit Tests (Phase 1):** Mock the Arize OTel traces. Ensure our Python evaluator correctly flags the mock "c3-standard" deployment trace as a failure.
* **Integration Tests (Phase 2):** Mock the `@arizeai/phoenix-mcp` server. Ensure AeroCaliper can invoke `get-spans`, receive the mock trace, and parse it without crashing.
* **Statefulness Tests (Phase 3):** Validate the Gemini 3.1 Pro **Thought Signatures**. Ensure the encrypted token received from the first generation is passed correctly to the Interactions API background job.
* **Egress Tests (Phase 4):** Ensure the `upsert-prompt` payload is properly intercepted by the mocked Model Armor Service Extension.

## 4. Security & Governance (Model Armor)
AeroCaliper's outbound connection to the Arize MCP server must be routed through **Google Cloud Agent Gateway**.
* We will define a Service Extension bound to the gateway.
* The Service Extension will use a `CONTENT_AUTHZ` profile linked to a Model Armor policy.
* **Test Case:** If AeroCaliper accidentally hallucinates a prompt injection attack (e.g., trying to drop the Arize database), Model Armor will block the egress payload, returning a 403 Forbidden.

## 5. Deployment Pipeline
1. **Local Dev:** Use `ngrok` or ADK local-runner to test the webhook triggers from Arize.
2. **Cloud Run:** Containerize AeroCaliper using Docker and deploy to Google Cloud Run.
3. **Demo Recording:** Execute the full flow locally while the browser agent records the Arize Dashboard updating live as the prompt is patched.
