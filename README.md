# AeroCaliper v4.0

**Autonomous AI Governance and Remediation Pipeline**

AeroCaliper is an enterprise-grade, fully autonomous remediation pipeline designed to detect policy violations in AI agent outputs, diagnose root causes, dynamically generate system prompt patches, and deploy those patches back into production.

Powered by the **Google Agent Platform**, **Arize Phoenix**, and the **Model Context Protocol (MCP)**, AeroCaliper seamlessly closes the loop between AI observability and continuous agent improvement.

---

## The AeroCaliper Advantage

When enterprise AI agents violate FinOps limits, HR privacy rules, or data handling protocols, the standard remediation cycle is slow: it involves manual log review, ticketing, prompt engineering, and redeploying code. 

**AeroCaliper solves this by completely automating the remediation lifecycle.**

1. **Detection:** Incoming requests are intercepted and scanned for anomalies using deterministic rules and Gemini-powered intent analysis.
2. **Diagnostic:** AeroCaliper retrieves failed OpenTelemetry execution traces directly from Arize Phoenix via MCP. It then queries **Vertex AI Search** to pull the relevant enterprise policy, feeding the trace and the policy to Gemini for root-cause analysis.
3. **LLM-as-a-Judge Backtesting:** Candidate prompt patches are subjected to rigorous empirical backtesting against a domain-specific golden dataset. Gemini runs simulated evaluations, self-refining the prompt up to three times until a 100% pass rate is achieved.
4. **Human-in-the-Loop Validation:** Successful patches are presented to administrators via a live Server-Sent Events (SSE) dashboard for final approval.
5. **Secure Egress:** The approved prompt passes through **Google Cloud Model Armor** for deep packet inspection. Once cleared, it is immediately deployed to the live Arize Prompt Registry via the `@arizeai/phoenix-mcp` server.

---

## Core Technologies

- **Google Agent Platform:** Orchestrates the multi-agent pipeline and drives all intelligent decision-making via `gemini-3.1-pro-preview`.
- **Arize Phoenix & MCP:** Utilizes the official Python SDK for the Model Context Protocol to seamlessly pull traces and push prompt updates directly to the Arize cloud, effectively closing the observability loop.
- **Google Cloud Model Armor:** Provides enterprise-grade egress inspection to ensure that no toxic, sensitive, or prohibited data is inadvertently leaked into the prompt registry.
- **Vertex AI Search:** Implements a decoupled compliance architecture. Organizational policies are maintained as natural language documents in GCP datastores. AeroCaliper uses Vertex AI's *Extractive Answers* to dynamically inject the most up-to-date policies into the evaluation rubric without requiring code deployments.

---

## Decoupled Compliance Architecture

AeroCaliper entirely decouples compliance logic from application code. Instead of hardcoding FinOps restrictions or HR privacy rules into the orchestrator, policies are maintained directly by stakeholders in Google Cloud Storage.

When an anomaly is detected, AeroCaliper uses `discoveryengine_v1.SearchServiceClient` to query Vertex AI Search, injecting the retrieved snippets directly into the LLM-as-a-Judge prompt template. 

---

## Quickstart

**Step 0: Environment Configuration**

```bash
cp .env.example .env
# Populate all required variables before proceeding.
# Required: GOOGLE_AGENT_PLATFORM_API_KEY, PHOENIX_API_KEY, GCP_PROJECT_ID,
#           ARIZE_SPACE_ID, MODEL_ARMOR_TEMPLATE, GCP_PROJECT_NUMBER
```

**Step 1: Install Dependencies**

```bash
pip install -r requirements.txt
```

**Step 2: Launch the AeroCaliper UI**

```bash
uvicorn main:app --host 127.0.0.1 --port 8080
```

**Step 3: Trigger Live Traces**

Run the target agent to simulate a workload routing decision and push OpenTelemetry traces to Arize Phoenix:

```bash
python target_agent.py --use-case finops
```

**Step 4: Explore the Demo**

Navigate to `notebooks/AeroCaliper_Demo.ipynb` for an interactive, executed walkthrough demonstrating the integration between Vertex AI Search, Arize Phoenix traces, and the LLM-as-a-Judge backtesting loop.
