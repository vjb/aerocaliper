# AeroCaliper: Mocks & Functional Limitations Log

Per project requirements, this document tracks all simulated functionality.

## Phase 1 & 2 Mocks
1. **Target Agent AI Core (`target_agent.py`)**: 
   - **Mock:** We simulate the Vertex AI LLM deployment logic using a deterministic Python `if/else` statement (`if "biggest" in prompt -> X5`). 
   - **Why:** To isolate the FinOps evaluation logic and guarantee the "Confused Deputy" hallucination occurs consistently for the hackathon baseline.

## Phase 3: 100% Functional MCP Integration
**We are using the OFFICIAL Arize Partner Track MCP Server.**
Our `NativeMCPClient` directly invokes `npx -y @arizeai/phoenix-mcp` and securely routes requests over JSON-RPC 2.0 stdio, perfectly fulfilling the strict requirements of the Google Cloud Rapid Agent Hackathon. **There is absolutely no mocking of the MCP architecture.**

1. **Gemini 3.1 Pro "Thought Signatures" & "Interactions API"**:
   - **Mock:** Since the "Gemini 3.1 Pro Interactions API with background=True" is a futuristic Google Cloud capability, we implement this functionally by making real POST requests to the current `gemini-flash-latest` model and simulating the async background job via `asyncio`. The "Thought Signature" is functionally implemented by passing the LLM's conversation context as a stateful dictionary between asynchronous tasks.
