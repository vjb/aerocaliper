# AeroCaliper v4.0

**Autonomous AI Governance and Remediation Pipeline**

AeroCaliper is a zero-trust compliance engine that uses its own observability data to improve over time. It detects policy violations, fetches failed traces via the Arize Phoenix MCP server, and uses a Gemini-driven optimization loop to autonomously patch and redeploy its own system prompt.

Powered by the **Google Agent Platform**, **Arize Phoenix**, and the **Model Context Protocol (MCP)**, AeroCaliper seamlessly closes the loop between AI observability and continuous agent improvement.

---

## 🏆 Google Cloud Rapid Agent Hackathon (Arize Track)

AeroCaliper was built to perfectly align with the core judging criteria of the Arize track: **"Ship agents that do more than run. Ship agents that can self improve."**

Here is exactly how AeroCaliper maps to the hackathon requirements:
- **Code-Owned Agent Runtime**: Built entirely from the ground up using the Google GenAI SDK (`gemini-3.1-pro-preview`) running as an asynchronous FastAPI application on Google Cloud Run.
- **Meaningful Use of Tracing**: Fully instrumented using the `openinference-instrumentation-google-genai` OpenTelemetry auto-instrumentor. 
- **Introspection via MCP**: Seamlessly integrates the `@arizeai/phoenix-mcp` server. It uses the `get-spans` tool to fetch its own failed traces, and `upsert-prompt` to deploy the repaired system prompts dynamically without a code redeployment.
- **LLM-as-a-Judge Evaluations**: Every candidate patch is passed through a rigorous empirical backtesting loop. Gemini runs simulated evaluations against a golden dataset, forcing the agent to self-refine up to three times until it achieves a 100% pass rate.
- **Iterative Self-Improvement Loop**: AeroCaliper is the epitome of an agent using its own observability data to improve over time. By pulling failed traces, augmenting them with Vertex AI Search for enterprise compliance rules, running automated backtests, and seamlessly updating the prompt registry, the agent autonomously self-heals in under two minutes.

---

## The AeroCaliper Advantage

When enterprise AI agents violate FinOps limits, HR privacy rules, or data handling protocols, the standard remediation cycle is slow: it involves manual log review, ticketing, prompt engineering, and redeploying code. 

**AeroCaliper solves this by completely automating the remediation lifecycle.**

1. **Detection:** Incoming requests are intercepted and scanned for anomalies using deterministic rules and Gemini-powered intent analysis.
2. **Diagnostic:** AeroCaliper retrieves failed OpenTelemetry execution traces directly from Arize Phoenix via MCP. It then queries **Vertex AI Search** to pull the relevant enterprise policy, feeding the trace and the policy to Gemini for root-cause analysis.
3. **LLM-as-a-Judge Backtesting:** Candidate prompt patches are subjected to rigorous empirical backtesting against a domain-specific golden dataset. Gemini runs simulated evaluations, self-refining the prompt up to three times until a 100% pass rate is achieved.
4. **Human-in-the-Loop Validation:** Successful patches are presented to administrators via a live Server-Sent Events (SSE) dashboard for final approval.
5. **Secure Egress:** The approved prompt passes through **Google Cloud Model Armor** for deep packet inspection. Once cleared, it is immediately deployed to the live Arize Prompt Registry via the `@arizeai/phoenix-mcp` server.

```mermaid
flowchart TD
    %% Styling
    classDef agent fill:#e8f0fe,stroke:#1a73e8,stroke-width:2px,color:#1a73e8;
    classDef GCP fill:#e6f4ea,stroke:#1e8e3e,stroke-width:2px,color:#1e8e3e;
    classDef Arize fill:#fce8e6,stroke:#d93025,stroke-width:2px,color:#d93025;
    classDef UI fill:#fef7e0,stroke:#f9ab00,stroke-width:2px,color:#b06000;

    subgraph UserSpace [Target Environment]
        User([End User Request]) --> TargetAgent[Target Agent\n(e.g., FinOps/HR)]
        TargetAgent -->|OpenTelemetry Traces| ArizeCloud
    end

    subgraph ArizeCloud [Arize Phoenix Cloud]
        TraceDB[(Trace DB)]
        PromptReg[(Prompt Registry)]
    end

    subgraph AeroCaliper [AeroCaliper Autonomous Remediation Pipeline]
        Detect[1. Anomaly Detection\n(Gemini Intent Scan)]
        MCPHandshake[2. fetch_failed_traces\n(Arize Phoenix MCP)]
        Diag[3. Root Cause Diagnostic\n(Gemini 3.1 Pro)]
        Judge{4. run_empirical_backtest\n(Gemini 3.1 Pro Backtester)}
        AdminUI[5. A2UI Admin Panel\n(Human-in-the-Loop)]
    end

    subgraph GCPCloud [Google Cloud Infrastructure]
        VertexRAG[(search_enterprise_policy\nVertex AI Search RAG)]
        Firestore[(query_past_remediations\nCloud Firestore)]
        ModelArmor[Model Armor\n(DPI Egress Filter)]
    end

    %% Flow
    TargetAgent -.->|Violation Detected| Detect
    Detect -->|Trigger Healing| MCPHandshake
    MCPHandshake <-->|get-spans| TraceDB
    MCPHandshake --> Diag
    
    Diag <-->|RAG Policy| VertexRAG
    Diag <-->|RAG Memory| Firestore
    
    Diag -->|Candidate Prompt| Judge
    Judge -.->|Failed Backtest| Diag
    Judge -->|100% Pass Rate| AdminUI
    
    AdminUI -->|Approve| ModelArmor
    ModelArmor -->|Secure Egress| MCPHandshake
    MCPHandshake <-->|deploy_prompt_patch\nupsert-prompt| PromptReg

    %% Class Assignments
    class TargetAgent,Detect,Diag,Judge agent;
    class VertexRAG,Firestore,ModelArmor GCP;
    class TraceDB,PromptReg,MCPHandshake Arize;
    class AdminUI UI;
```

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

## Thought Signatures & Audit Trails

To comply with strict enterprise governance requirements, AeroCaliper generates a **Thought Signature** for every candidate prompt patch before it is presented to an administrator.

A Thought Signature (e.g., `sig_v4_ccdd57`) is a cryptographic checksum of the exact string contents of the candidate prompt generated by Gemini. This ensures that:
1. **Integrity:** The exact prompt text that the LLM-as-a-Judge evaluated and that the admin approved is mathematically guaranteed to be the exact prompt that gets passed to Model Armor and deployed to the registry.
2. **Auditability:** Security teams can cross-reference the Thought Signature in the UI logs with the final version deployed in Arize Phoenix to prove no tampering occurred during the automated remediation loop.

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
