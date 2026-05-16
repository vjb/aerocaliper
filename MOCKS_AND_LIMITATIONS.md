# AeroCaliper: Mocks & Functional Limitations Log

Per project requirements, this document tracks all simulated functionality.

## Phase 1 & 2 Mocks
1. **Target Agent AI Core (`target_agent.py`)**: 
   - **Mock:** We simulate the Vertex AI LLM deployment logic using a deterministic Python `if/else` statement (`if "biggest" in prompt -> X5`). 
   - **Why:** To isolate the FinOps evaluation logic and guarantee the "Confused Deputy" hallucination occurs consistently for the hackathon baseline.

## Phase 3: The 100% Functional MCP Engine
Unlike Phase 1, **the MCP Architecture is completely functional.**
We bypassed the external dependency constraint (Python 3.8 vs the official Anthropic SDK) by writing a native Python `NativeMCPClient` and `phoenix_mcp_server.py`. 
These components communicate natively over `stdio` using strict JSON-RPC 2.0 formatting, precisely matching the official Model Context Protocol standard. 

1. **Gemini 3.1 Pro "Thought Signatures" & "Interactions API"**:
   - **Mock:** Since the "Gemini 3.1 Pro Interactions API with background=True" is a futuristic 2026 Google Cloud feature, we implement this functionally by making real POST requests to the current Gemini API (`gemini-flash-latest`) and simulating the async background job via `asyncio`. The "Thought Signature" is functionally implemented by passing the LLM's conversation context as a stateful dictionary between asynchronous tasks.
