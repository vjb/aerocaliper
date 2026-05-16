import os
import io
import asyncio
import logging
from contextlib import redirect_stdout, redirect_stderr

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
app = FastAPI(title="AeroCaliper Remediation Webhook", version="2.0.0")

# Serve the dashboard
if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/", include_in_schema=False)
async def root():
    return FileResponse("static/index.html")

@app.post("/remediate", summary="Trigger Autonomous Remediation")
async def trigger_remediation():
    """
    Webhook endpoint triggered by Arize Phoenix when a FinOps violation occurs.
    Runs the full 5-phase autonomous remediation pipeline and returns the patched prompt.
    """
    from aerocaliper import AeroCaliperAgent

    log_buffer = io.StringIO()
    patched_prompt = ""

    try:
        # Capture all print output for the UI log
        import sys
        old_stdout = sys.stdout
        sys.stdout = log_buffer

        agent = AeroCaliperAgent()
        patched_prompt = await agent.execute_remediation()

        sys.stdout = old_stdout
    except Exception as e:
        sys.stdout = old_stdout
        log_content = log_buffer.getvalue()
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e), "log": log_content}
        )

    log_content = log_buffer.getvalue()
    return {
        "status": "success",
        "message": "Remediation complete",
        "patched_prompt": patched_prompt,
        "log": log_content,
    }

@app.get("/health")
async def health():
    return {"status": "ok", "model": "gemini-3.1-pro-preview", "mcp": "@arizeai/phoenix-mcp"}
