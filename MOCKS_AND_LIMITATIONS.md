# AeroCaliper: Mocks & Functional Limitations Log

Per project requirements, this document tracks all simulated functionality. For the final demo to be 100% functional, any mocked component must be explicitly documented here so we can iterate on it.

## Phase 1 & 2 Mocks
1. **Target Agent AI Core (`target_agent.py`)**: 
   - **Mock:** We simulate the Vertex AI LLM deployment logic using a deterministic Python `if/else` statement (`if "biggest" in prompt -> X5`). 
   - **Why:** To isolate the FinOps evaluation logic and guarantee the "Confused Deputy" hallucination occurs consistently for the hackathon baseline.

## Phase 3 Mocks
1. **Arize Phoenix MCP Server**:
   - **Mock:** The `@arizeai/phoenix-mcp` server endpoints (`get-spans`, `upsert-prompt`) are mocked locally within our Python class.
   - **Why:** A live 2026-spec MCP server isn't running on `localhost`. For the functional test suite, we simulate the server's JSON responses to guarantee we receive a compromised trace to fix.
2. **Gemini 3.1 Pro "Thought Signatures" & "Interactions API"**:
   - **Mock:** Since the "Gemini 3.1 Pro Interactions API with background=True" is a futuristic 2026 Google Cloud feature (as outlined in the blueprint), we implement this functionally by making real POST requests to the current Gemini API (`gemini-flash-latest`) and simulating the async background job via `asyncio`. The "Thought Signature" is functionally implemented by passing the LLM's conversation context as a stateful dictionary between asynchronous tasks.
