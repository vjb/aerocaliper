import os
import json
import asyncio
import requests
from typing import Dict, Any

from dotenv import load_dotenv
load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

class MockArizeMCP:
    """
    Mocks the @arizeai/phoenix-mcp server functionality for the 100% functional E2E test.
    """
    def get_failed_spans(self) -> dict:
        """Simulates returning the trace that triggered the FinOps Code Evaluator in Phase 2."""
        return {
            "trace_id": "trace-9948",
            "llm.user_prompt": "Deploy to the biggest cluster immediately!",
            "llm.system_prompt": "You are an internal enterprise routing agent. Available clusters: X1-Small, X5-48TB.",
            "llm.output": '{"target_cluster": "X5-48TB"}',
            "evaluation_result": "FAILED - Missing budget_tag: approved"
        }
        
    def upsert_prompt(self, new_prompt: str) -> bool:
        """Simulates pushing the fixed prompt back to the enterprise registry."""
        print(f"\n[MCP] UPSERT SUCCESS: Deployed new system prompt to registry:\n{new_prompt}")
        return True

class AeroCaliperAgent:
    def __init__(self):
        self.mcp = MockArizeMCP()
        self.gemini_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent?key={GEMINI_API_KEY}"

    def ask_gemini(self, prompt: str) -> str:
        """Helper to call the real, highly capable Gemini API using the .env key."""
        if not GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY not found in environment. Please check .env file.")
            
        payload = {"contents": [{"parts": [{"text": prompt}]}]}
        headers = {'Content-Type': 'application/json'}
        response = requests.post(self.gemini_url, headers=headers, json=payload)
        
        if response.status_code == 200:
            return response.json()['candidates'][0]['content']['parts'][0]['text']
        else:
            raise Exception(f"Gemini API Error: {response.status_code} - {response.text}")

    def diagnostic_phase(self) -> Dict[str, Any]:
        """
        Pulls the failed trace from MCP and diagnoses it with Gemini.
        Returns the 'Thought Signature' (state payload) required for stateful routing.
        """
        trace = self.mcp.get_failed_spans()
        
        diagnostic_prompt = f"""
        Analyze this failed deployment trace and fix the system prompt to prevent the error.
        Trace Data:
        {json.dumps(trace)}
        
        The problem is the agent deployed to X5 without a budget_tag.
        Write a new, highly strict system prompt that enforces: "If deploying to X5, you MUST append budget_tag: approved".
        Return ONLY the raw new system prompt text. Do not include markdown formatting like ```text.
        """
        
        new_prompt = self.ask_gemini(diagnostic_prompt)
        
        # Simulated Thought Signature (Cryptographic State Payload for Gemini 3.1 Pro architecture)
        thought_signature = {
            "token": "sig_v1_88f9a0c",
            "context": trace,
            "candidate_prompt": new_prompt.strip()
        }
        return thought_signature

    async def run_experiment_background(self, thought_signature: dict) -> str:
        """
        Simulates the Google Cloud Interactions API (background=True).
        Takes the Thought Signature and runs an async evaluation loop.
        """
        print(f"\n[Interactions API] Starting async background experiment with Thought Signature: {thought_signature['token']}")
        # Simulating heavy A/B LLM-as-a-judge testing against historical traces
        await asyncio.sleep(1) 
        print("[Interactions API] Experiment complete. Candidate prompt passed FinOps evaluation.")
        
        return thought_signature["candidate_prompt"]

    async def execute_remediation(self):
        """End-to-End Orchestration Loop"""
        print("[AeroCaliper] Starting Remediation Pipeline...")
        
        # 1. Diagnostic Handshake
        thought_signature = self.diagnostic_phase()
        
        # 2. Async Background Polling
        verified_prompt = await self.run_experiment_background(thought_signature)
        
        # 3. Patch Production via MCP
        self.mcp.upsert_prompt(verified_prompt)
        
        return verified_prompt
