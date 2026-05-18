# AeroCaliper Hackathon Submission Checklist

**Deadline:** June 11

Before hitting "Submit" on Devpost or the partner portal, ensure all items on this list have been double-checked. This project relies on live integrations with GCP and Arize, meaning API deprecations or temporary outages can break the demo.

## 1. Google Cloud / Vertex AI Readiness
- [ ] **GCP Project Verification:** Ensure `GOOGLE_CLOUD_PROJECT` is set to the live project ID (e.g., `aerocaliper-demo`).
- [ ] **Vertex Search Datastores Active:** 
  - Log into GCP Console -> Vertex AI Search and Conversation -> AI Applications.
  - Verify that `AeroCaliper HR Privacy Policy Search` (`hr-app`) and `AeroCaliper FinOps Policy Search` (`finops-app`) are still active.
  - Test a manual query in the console to ensure indexing hasn't stalled and Extractive Answers are returning correctly.
- [ ] **Model Armor Policies:** If the `MODEL_ARMOR_TEMPLATE` environment variable is used for the demo, verify the policy exists in the GCP console and isn't blocking legitimate traffic. (Local fallback is available but live is better).
- [ ] **Gemini Quotas:** Verify that `gemini-3.1-pro-preview` limits haven't been exhausted.

## 2. Arize Phoenix & MCP Integrations
- [ ] **Workspace ID Configuration:** Verify `ARIZE_SPACE_ID` in the `.env` file matches the live workspace URL (e.g., `https://app.phoenix.arize.com/s/<ID>`).
- [ ] **API Keys:** Ensure `PHOENIX_API_KEY` is still valid.
- [ ] **The 500 Error (Prompt Upserting):** 
  - **CRITICAL:** Check if the `upsert-prompt` via MCP is still returning a `500 Internal Server Error` from Arize Cloud. 
  - If it is, heavily lean into the "Zero-Trust Fail-Closed" talking point in the video pitch. Do not try to hack around it at the last minute; frame it as a deliberate security feature.
- [ ] **Live Trace Ingestion:** Run a quick manual test to ensure traces are actively appearing in the Arize UI.

## 3. Demo Recording / Video Pitch
- [ ] **Show the GCP Console:** Explicitly show the Vertex AI Search Apps to visually prove the Decoupled Compliance architecture. 
- [ ] **Show the Terminal:** Run `python scripts/scratch.py` live to show the pipeline discovering the MCP environment, fetching traces, performing RAG, running the Golden Dataset backtest, and hitting the LLM Judge.
- [ ] **Highlight the Notebooks:** Briefly show `notebooks/Vertex_RAG_and_Arize_Eval_Deep_Dive_EXECUTED.ipynb` to prove the integration.

## 4. Documentation & Repository Polish
- [ ] **Golden Dataset:** Audit `golden_dataset.csv` one final time to ensure the test cases are clean and visually understandable for a judge browsing the repo.
- [ ] **README Quality:** Ensure the README accurately reflects the Vertex RAG architecture and explicitly calls out the Google Cloud & Arize Partner Track.
- [ ] **Sanitization:** Ensure no API keys or PII have accidentally slipped into commit histories.
