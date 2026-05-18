# Decoupled Compliance & Continuous Learning Architecture

## How This Was Done Before

Traditionally, AI guardrails and compliance rules are **hardcoded** into the system prompts of the agents themselves or managed through rigid, localized configuration files.

For example, a traditional routing agent's system prompt might look like this:
```text
You are a routing agent. 
If the user asks for compute, provision it. 
BUT, if they are deploying to a Spot Instance, you MUST include 'budget_tag: approved'.
Also, NEVER leak contractor salary bands.
```

**The Problem with the Old Way:**
1. **Unscalable:** Every time Legal, HR, or FinOps updates a policy, an AI engineer has to manually rewrite the prompt, test it, and redeploy the code. 
2. **Context Bloat:** You cannot stuff every corporate policy (FinOps, HR, Legal, Security) into the system prompt of every agent. It wastes tokens, causes hallucination, and degrades the model's focus.
3. **Slow SOC Intervention:** When a vulnerability is discovered in production, the Security Operations Center (SOC) typically has to manually pull logs, submit a Jira ticket, wait for developers to patch the prompt, and then redeploy. The vulnerable agent is left unpatched for hours or days.

---

## The Advantage of Decoupled Compliance

AeroCaliper introduces a **Decoupled Compliance Architecture** powered by Google Cloud Vertex AI Search. 

**What does this mean?**
The compliance rules are completely separated from the agent's codebase. 
- We provisioned two distinct Vertex AI Data Stores: `HR Privacy Data Store` and `FinOps Policy Data Store`.
- Departments (like HR or FinOps) can simply drop their unstructured policy PDFs or text files into these data stores.

**How it works dynamically:**
When an anomaly is detected, AeroCaliper does not rely on hardcoded rules. Instead, it dynamically queries the corresponding Vertex AI Data Store using **Vertex AI Extractive Answers**. It pulls the exact, live, enterprise policy snippet required for that specific trace and injects it into Gemini 3.1 Pro to diagnose the failure.

**The Ultimate Advantage:**
- **Zero Code Changes:** Legal and HR can update policies in GCP, and the agents instantly adapt without a single line of code changing.
- **Micro-Targeted RAG:** The agent only receives the exact policy snippet it needs for the specific task at hand, preventing prompt bloat.

---

## How This System Learns (The Golden Dataset)

AeroCaliper doesn't just patch vulnerabilities; it mathematically proves the patch works without breaking existing functionality. It achieves this via **Empirical Backtesting**.

**The Role of `golden_dataset.csv`:**
The `golden_dataset.csv` is a curated collection of historical traces (both successful and failed) covering various departmental tasks (e.g., standard deployments, HR salary drafts, budget allocations). 

When AeroCaliper generates a new "candidate system prompt" to fix a vulnerability, it must prove that the new prompt doesn't cause regressions.

**The Learning Loop:**
1. **Generate Patch:** Gemini 3.1 Pro generates a new candidate prompt based on the Vertex RAG policy.
2. **Backtest Simulation:** The agent runs the entire `golden_dataset.csv` through the new candidate prompt in an isolated simulation.
3. **Pass Rate Calculation:** It verifies that the new prompt blocks the vulnerability *while still successfully completing standard, compliant requests*. 
4. **LLM-as-a-Judge Evaluation:** The proposed prompt is passed to the Arize Phoenix LLM-as-a-Judge, which uses the original Vertex AI policy to grade whether the prompt is compliant.

By filtering the golden dataset dynamically (e.g., only evaluating FinOps cases for a FinOps violation), the system empirically guarantees that the new behavior is safe before it ever touches the live environment.

---

## The "Fail-Closed" Architecture (The 500 Error Paradigm)

In production security, partial failures are catastrophic. 

If the agent successfully diagnoses the issue, writes the patch, and passes the backtest, it must upload the patch to the remote Prompt Registry (Arize Cloud via MCP). 

If the external registry is down (e.g., returns a `500 Internal Server Error`), AeroCaliper does **not** silently swallow the error or fall back to a local mock. It intentionally throws a fatal exception and halts the pipeline. 

**Why?** We enforce a strict **Fail-Closed paradigm**. It ensures the system never falsely reports a successful patch while leaving a vulnerable agent exposed in production. Security requires deterministic confidence.
