# AeroCaliper - Google Cloud Rapid Agent Hackathon

## 💡 Inspiration
We noticed a critical gap in enterprise AI adoption: while organizations are eager to deploy agentic workflows, the financial and operational risks of a "hallucination loop" are too high. We were inspired to build a solution that doesn't just *monitor* these agents, but actively *heals* them using Google Cloud's bleeding-edge infrastructure and Arize Phoenix observability.

## ⚙️ What it does
AeroCaliper is an autonomous debugging and remediation agent. If an internal enterprise routing agent makes a critical mistake (like deploying an expensive cluster without a budget tag), AeroCaliper detects the failure via Arize Phoenix OpenTelemetry. It then securely connects via Google Cloud Agent Gateway, diagnoses the trace using Gemini 3.1 Pro (utilizing Thought Signatures), and asynchronously pushes a tested patch to the system prompt to prevent the error from happening again.

## 🛠️ How we built it
- **Core Orchestration:** Google Cloud Agent Development Kit (ADK) in Python.
- **Intelligence:** Gemini 3.1 Pro with the Interactions API for long-horizon background testing.
- **Security:** Model Armor via Service Extensions on the Agent Gateway to secure egress traffic.
- **Observability:** Arize Phoenix MCP Server & Code Evaluators.

## 🚧 Challenges we ran into
Handling state persistence across multi-turn tool calls was extremely difficult. If the agent lost context after fetching traces from Arize, it couldn't reliably patch the prompt. We overcame this by implementing Gemini 3.1 Pro's new **Thought Signatures**, ensuring the cryptographic reasoning state was preserved across the Interactions API.

## 🏆 Accomplishments that we're proud of
We successfully demonstrated a zero-touch, closed-loop remediation of a live agent. We took the Mean Time to Resolution (MTTR) of an AI deployment failure from potentially hours of human debugging down to seconds of machine-speed patching.

## 🎓 What we learned
We learned that observability is no longer just a dashboard—it's a control plane. By combining Arize's OpenTelemetry data with Google Cloud's ADK, agents can literally rewrite their own flawed logic based on real-world failures.

## 🚀 What's next for AeroCaliper
We plan to expand the Code Evaluators to include real-time cybersecurity metrics, allowing AeroCaliper to instantly quarantine compromised agents and rewrite their boundary logic the second a prompt injection is detected.
