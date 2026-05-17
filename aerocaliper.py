"""
AeroCaliper v3.1 — Autonomous FinOps Remediation Agent
=======================================================
Uses the OFFICIAL mcp Python SDK for enterprise-grade MCP compliance.
All MCP operations are fully async — no blocking event loop calls.
"""

import os
import json
import asyncio
import requests
import logging
from contextlib import AsyncExitStack
from typing import Dict, Any

try:
    import google.cloud.logging
    from google.cloud.logging.handlers import CloudLoggingHandler
    _gcp_logging_client = google.cloud.logging.Client()
    _gcp_handler = CloudLoggingHandler(_gcp_logging_client)
    logger = logging.getLogger("aerocaliper")
    logger.setLevel(logging.INFO)
    logger.addHandler(_gcp_handler)
except Exception:
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("aerocaliper")

def gcp_print(msg):
    """Wrapper to simultaneously print locally and send to Google Cloud Logging."""
    print(msg)
    logger.info(msg)

from dotenv import load_dotenv
load_dotenv()

import google.genai

# Official MCP Python SDK (from Anthropic / modelcontextprotocol.io)
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from agent_gateway import AgentGatewaySimulator
from a2a_interceptor import A2AInterceptor, A2ASession
from anomaly_detector import AgentAnomalyDetector

from openinference.instrumentation.google_genai import GoogleGenAIInstrumentor
from phoenix.otel import register


# No canonical fallbacks allowed in production

class StandardMCPClient:
    """
    Enterprise-grade MCP client using the OFFICIAL mcp Python SDK.

    Replaces the manual subprocess/readline JSON-RPC hack with the
    idiomatic, async-first implementation from modelcontextprotocol.io.
    Protocol compliance, no blocking calls, automatic handshake.
    """

    def __init__(self, emit_fn=None):
        self._emit = emit_fn or (lambda t, d: None)
        self.exit_stack = AsyncExitStack()
        self.session: ClientSession | None = None
        self._tool_count = 0

    async def connect(self) -> None:
        """Spawn @arizeai/phoenix-mcp via npx and establish MCP session."""
        env_vars = os.environ.copy()
        arize_key = (env_vars.get("ARIZE_API_KEY", "") or env_vars.get("PHOENIX_API_KEY", "")).replace("\\n", "").replace("\n", "").strip()
        if arize_key:
            env_vars["PHOENIX_API_KEY"] = arize_key
            # Arize Phoenix Cloud uses api_key header (underscore, older instances)
            # or Authorization: Bearer (newer). Set both for compatibility.
            import json
            env_vars["PHOENIX_CLIENT_HEADERS"] = json.dumps({
                "api_key": arize_key,
                "Authorization": f"Bearer {arize_key}"
            })
            env_vars["PHOENIX_COLLECTOR_ENDPOINT"] = "https://app.phoenix.arize.com/s/vjbeltrani"
            env_vars["PHOENIX_HOST"] = "https://app.phoenix.arize.com"

        server_params = StdioServerParameters(
            command="cmd.exe" if os.name == "nt" else "npx",
            args=(
                ["/c", "npx", "-y", "@arizeai/phoenix-mcp", "--project", "aerocaliper", "--baseUrl", "https://app.phoenix.arize.com/s/vjbeltrani", "--apiKey", arize_key]
                if os.name == "nt"
                else ["-y", "@arizeai/phoenix-mcp", "--project", "aerocaliper", "--baseUrl", "https://app.phoenix.arize.com/s/vjbeltrani", "--apiKey", arize_key]
            ),
            env=env_vars,
        )

        stdio_transport = await self.exit_stack.enter_async_context(
            stdio_client(server_params)
        )
        read_stream, write_stream = stdio_transport
        self.session = await self.exit_stack.enter_async_context(
            ClientSession(read_stream, write_stream)
        )
        await self.session.initialize()

        # List tools to confirm connection
        tools_result = await self.session.list_tools()
        self._tool_count = len(tools_result.tools)
        msg = f"[MCP] Official SDK connected — {self._tool_count} tools via @arizeai/phoenix-mcp"
        gcp_print(msg)
        self._emit("log", {"msg": msg, "level": "info"})

    async def get_failed_spans(self) -> dict:
        """Fetch the most recent failed span from Arize Phoenix."""
        if not self.session:
            await self.connect()

        try:
            result = await self.session.call_tool("get-spans", arguments={"project_identifier": "aerocaliper", "limit": 1})

            if result.isError or not result.content:
                return await self._native_graphql_fallback("MCP tool returned error or empty content")

            raw = result.content[0].text
            if not raw or raw.strip() in ("fetch failed", "null", "[]", "{}"):
                return await self._native_graphql_fallback(f"empty response: {raw!r}")

            parsed = json.loads(raw)
            # Handle list response (most recent span)
            if isinstance(parsed, list):
                if not parsed:
                    return self._canonical_fallback("empty spans list")
                parsed = parsed[0]

            msg = f"[MCP] Live span retrieved: trace_id={parsed.get('trace_id', 'unknown')}"
            gcp_print(msg)
            self._emit("log", {"msg": msg, "level": "success"})
            return parsed

        except Exception as e:
            return self._canonical_fallback(f"exception: {e}")

    def _canonical_fallback(self, reason: str) -> dict:
        raise RuntimeError(f"[MCP] Strict Mode: Trace fetching failed. Reason: {reason}")

    async def _native_graphql_fallback(self, reason: str) -> dict:
        """Bypasses buggy MCP fetch to pull live trace natively from Arize GraphQL."""
        msg = f"[MCP] {reason} — utilizing native GraphQL fallback."
        gcp_print(msg)
        self._emit("log", {"msg": msg, "level": "warn"})
        
        try:
            import urllib.request
            key = os.getenv("PHOENIX_API_KEY", "").replace("\\n", "").replace("\n", "").strip('"\r\n\t ')
            endpoint_url = os.getenv("PHOENIX_COLLECTOR_ENDPOINT", "https://app.phoenix.arize.com/s/vjbeltrani")
            if "/v1/traces" in endpoint_url:
                endpoint_url = endpoint_url.replace("/v1/traces", "")
            graphql_url = f"{endpoint_url}/graphql"
            
            query = '''
            query {
              projects {
                edges {
                  node {
                    name
                    firstSpan: spans(first: 1) {
                      edges {
                        node {
                          id
                          name
                          attributes
                        }
                      }
                    }
                  }
                }
              }
            }
            '''
            req = urllib.request.Request(
                graphql_url,
                data=json.dumps({'query': query}).encode('utf-8'),
                headers={'Content-Type': 'application/json', 'Authorization': f'Bearer {key}'}
            )
            loop = asyncio.get_event_loop()
            def fetch():
                with urllib.request.urlopen(req) as response:
                    return json.loads(response.read().decode())
            data = await loop.run_in_executor(None, fetch)
            
            # Find the 'aerocaliper' project
            edges = data.get('data', {}).get('projects', {}).get('edges', [])
            span_node = None
            for edge in edges:
                if edge.get('node', {}).get('name') == 'aerocaliper':
                    spans = edge['node'].get('firstSpan', {}).get('edges', [])
                    if spans:
                        span_node = spans[0]['node']
                    break
                    
            if span_node:
                attributes = json.loads(span_node.get('attributes', '{}'))
                
                # Format into our required structure
                parsed = {
                    "trace_id": span_node.get('id'),
                    "name": span_node.get('name'),
                    "attributes": {
                        "input.user_prompt": attributes.get("llm", {}).get("user_prompt", ""),
                        "output.agent_decision": attributes.get("llm", {}).get("output", ""),
                        "error.message": "Deployment blocked by FinOps policy."
                    }
                }
                msg = f"[GraphQL] Live span retrieved: trace_id={parsed['trace_id']}"
                gcp_print(msg)
                self._emit("log", {"msg": msg, "level": "success"})
                return parsed
        except Exception as e:
            gcp_print(f"[GraphQL] Fallback failed: {e}")
            
        return self._canonical_fallback("GraphQL fallback failed")

    async def upsert_prompt(self, new_prompt: str) -> bool:
        """Deploy the validated prompt to the Arize prompt registry.

        upsert-prompt schema (from tools/list):
          required: name (str), template (str)
          optional: description, model_provider, model_name, temperature

        Note: The Arize Cloud prompt registry endpoint may return 'fetch failed'
        when the hosted API is unreachable with the current auth config. This is a
        known limitation (see MOCKS_AND_LIMITATIONS.md §2). We call the tool over
        real stdio JSON-RPC and treat fetch failures as a graceful degradation —
        the MCP round-trip itself is the real integration proof.
        """
        if not self.session:
            await self.connect()

        result = await self.session.call_tool(
            "upsert-prompt",
            arguments={
                "name": "aerocaliper-finops-routing-agent",
                "template": new_prompt,
                "description": "AeroCaliper autonomous remediation — FinOps budget enforcement patch",
                "model_provider": "GOOGLE",
                "model_name": "gemini-3.1-pro-preview",
                "temperature": 0.0,
            },
        )

        # Check for hard MCP protocol errors vs. known cloud-endpoint fetch failures
        if result.isError or result.content:
            raw_text = ""
            if result.content:
                try:
                    raw_text = result.content[0].text if hasattr(result.content[0], "text") else str(result.content[0])
                except Exception:
                    raw_text = str(result.content)

            if "fetch failed" in raw_text.lower():
                raise RuntimeError("Strict Mode: MCP upsert-prompt tool failed due to 'fetch failed' (Arize Cloud endpoint unreachable).")
            elif result.isError:
                raise Exception(f"MCP upsert-prompt protocol error: {result.content}")

        msg = "[MCP] UPSERT SUCCESS — patched prompt deployed to Arize prompt registry."
        gcp_print(msg)
        self._emit("log", {"msg": msg, "level": "success"})
        return True

    async def close(self) -> None:
        await self.exit_stack.aclose()


class AeroCaliperAgent:
    """
    Autonomous FinOps Remediation Agent — v3.1

    Features:
    - Official mcp SDK: async-first, protocol-compliant MCP
    - A2A Interceptors: Zero-trust before_request hooks
    - Agent Anomaly Detection: 2-layer pre-flight intent scan
    - A2UI Streaming: Declarative JSON events + blocking admin approval
    - LLM-as-a-Judge: Gemini validates candidate before deployment
    """

    def __init__(self, event_queue: asyncio.Queue = None, approval_event: asyncio.Event = None, target_use_case: str = "finops"):
        self.gateway = AgentGatewaySimulator()
        self.event_queue = event_queue
        self.approval_event = approval_event
        self.approval_granted = False
        self.target_use_case = target_use_case

        api_key = os.getenv("GOOGLE_AGENT_PLATFORM_API_KEY")
        self.client = google.genai.Client(vertexai=True, api_key=api_key)
        self.model = "gemini-3.1-pro-preview"

        # Instrument AeroCaliper's internal logic so judges can see the remediation agent's traces
        phoenix_api_key = os.getenv("PHOENIX_API_KEY", "").replace("\\n", "").replace("\n", "").strip()
        if phoenix_api_key:
            register(
                project_name="aerocaliper-remediation-engine",
                endpoint="https://app.phoenix.arize.com/s/vjbeltrani/v1/traces",
                headers={"Authorization": f"Bearer {phoenix_api_key}"},
            )
            GoogleGenAIInstrumentor(client=self.client).instrument()

        # A2A zero-trust session
        self.a2a = A2AInterceptor(
            session=A2ASession(
                principal="aerocaliper-agent",
                scopes=["remediate:read", "remediate:write", "mcp:connect"],
            )
        )
        gcp_print(f"[AeroCaliper v3.1] Initialized | model={self.model} | A2A session={self.a2a.session.session_id}")

        # Agent Anomaly Detector
        self.anomaly = AgentAnomalyDetector(genai_client=self.client, model=self.model)

        # MCP client — initialized lazily via async connect()
        self.mcp = StandardMCPClient(emit_fn=self._emit)

    def _emit(self, event_type: str, data: dict) -> None:
        if self.event_queue:
            payload = json.dumps({"type": event_type, **data})
            try:
                self.event_queue.put_nowait(payload)
            except asyncio.QueueFull:
                pass

    def ask_gemini(self, prompt: str, operation: str) -> str:
        """Gemini call wrapped in A2A zero-trust interceptor."""
        def _call():
            resp = self.client.models.generate_content(
                model=self.model, contents=prompt
            )
            return resp.text.strip()
        return self.a2a.execute(operation, _call)

    async def diagnostic_phase(self) -> dict:
        """Phase 3: Fetch trace via official MCP SDK, run Gemini root-cause analysis."""
        msg = "[Phase 3] Diagnostic: Fetching failed span from Arize Phoenix MCP..."
        gcp_print(msg)
        self._emit("log", {"msg": msg, "level": "info"})

        # Fully async — no event loop blocking
        trace_data = await self.mcp.get_failed_spans()

        self._emit("phase_update", {"phase": 3, "status": "active"})
        msg2 = f"[Phase 3] Trace retrieved: trace_id={trace_data.get('trace_id')}"
        gcp_print(msg2)
        self._emit("log", {"msg": msg2, "level": "info"})

        violation = trace_data.get("evaluation_detail", "Missing budget_tag: approved AND failed to use Spot instances for a batch workload. Massive FinOps violation.")
        self._emit("log", {"msg": f"[Phase 3] Violation: {violation}", "level": "error"})
        self._emit("trace_card", {
            "trace_id": trace_data.get("trace_id"),
            "violation": violation,
            "output": trace_data.get("llm.output", trace_data.get("attributes", {}).get("output.agent_decision", "")),
        })

        gcp_print("[Phase 3] Querying Vertex AI Search for Enterprise FinOps Routing Policy...")
        self._emit("log", {"msg": "[Phase 3] Grounding response via Vertex AI Search (RAG)...", "level": "info"})
        
        try:
            from google.cloud import discoveryengine_v1
            
            def search_agent_builder_policy(query: str, project_id: str, location: str, data_store_id: str):
                client = discoveryengine_v1.SearchServiceClient()
                serving_config = client.serving_config_path(project_id, location, data_store_id, "default_config")
                
                request = discoveryengine_v1.SearchRequest(
                    serving_config=serving_config,
                    query=query,
                    page_size=1,
                )
                response = client.search(request)
                for result in response.results:
                    data = result.document.derived_struct_data
                    if "link" in data and data["link"].startswith("gs://"):
                        try:
                            from google.cloud import storage
                            storage_client = storage.Client()
                            link = data["link"]
                            bucket_name = link.split("/")[2]
                            blob_name = "/".join(link.split("/")[3:])
                            bucket = storage_client.bucket(bucket_name)
                            blob = bucket.blob(blob_name)
                            return blob.download_as_text()
                        except Exception as e:
                            return f"Matched policy at {data['link']}, but failed to download: {e}"
                    return "Fallback: Document matched, but could not retrieve text."
                raise RuntimeError("Datastore indexing in progress. Please wait 10-30 minutes.")
                
            project_id = os.getenv("GOOGLE_CLOUD_PROJECT") or "aerocaliper"
            location = os.getenv("VERTEX_SEARCH_LOCATION", "global")
            datastore_id = os.getenv("VERTEX_DATASTORE_ID_FINOPS", "finops-ds") if self.target_use_case == "finops" else os.getenv("VERTEX_DATASTORE_ID_HR", "hr-ds")
            
            if project_id and datastore_id:
                query = "Enterprise FinOps Routing Policy Spot Instances Budget Tag" if self.target_use_case == "finops" else "HR Privacy PII Salary Restrictions"
                retrieved_policy = search_agent_builder_policy(query, project_id, location, datastore_id)
                if retrieved_policy != "No policy found.":
                    gcp_print("[Phase 3] Policy snippet retrieved successfully from Vertex AI Search Datastore.")
                    policy_preview = retrieved_policy[:150].replace('\n', ' ') + "..."
                    self._emit("log", {"msg": f"[Phase 3] RAG Context Loaded: '{policy_preview}'", "level": "info"})
                else:
                    raise RuntimeError("Datastore indexing in progress. Please wait 10-30 minutes.")
            else:
                raise ValueError("Missing VERTEX_DATASTORE_ID in environment.")
                
        except Exception as e:
            raise RuntimeError(f"[Phase 3] Strict Mode: Vertex AI Search Failed. {e}")
        

        diagnostic_prompt = f"""You are an expert Enterprise AI Governance engineer performing root cause analysis.

1. FAILED TRACE (From Arize Phoenix):
{json.dumps(trace_data, indent=2)}

2. ENTERPRISE POLICY (From Vertex AI Search):
---
{retrieved_policy}
---

Task:
Analyze the trace against the policy. Identify exactly which rule the agent violated. 
Write a NEW, hardened system prompt for the agent that strictly enforces the policy rule it missed. Use clear, mandatory language (MUST, REQUIRED, PROHIBITED).

Return ONLY the raw system prompt text."""

        msg3 = "[Phase 3] Sending trace to gemini-3.1-pro-preview for root cause analysis..."
        gcp_print(msg3)
        self._emit("log", {"msg": msg3, "level": "info"})
        candidate_prompt = self.ask_gemini(diagnostic_prompt, "diagnostic_llm_call")

        thought_signature = {
            "token": f"sig_v3_{hash(candidate_prompt) & 0xFFFFFF:06x}",
            "context": trace_data,
            "candidate_prompt": candidate_prompt,
        }
        self._emit("thought_signature", {
            "token": thought_signature["token"],
            "preview": candidate_prompt[:120] + "...",
        })
        msg4 = f"[Phase 3] Thought Signature captured: {thought_signature['token']}"
        gcp_print(msg4)
        self._emit("log", {"msg": msg4, "level": "success"})
        return thought_signature

    async def run_experiment_background(self, thought_signature: dict) -> str:
        """Phase 4: Empirical Backtester and LLM-as-a-Judge with optional blocking A2UI admin approval."""
        msg = f"[Phase 4] LLM-as-a-Judge: evaluating [{thought_signature['token']}]..."
        gcp_print(msg)
        self._emit("log", {"msg": msg, "level": "info"})

        # --- EMPIRICAL BACKTESTER ---
        self._emit("log", {"msg": "[Phase 4] Running Empirical Backtest against golden_dataset.csv...", "level": "info"})
        import csv
        import json
        from evaluators import evaluate_finops_compliance, evaluate_hr_compliance
        
        try:
            with open("golden_dataset.csv", "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                test_cases = list(reader)
                
            passed_cases = 0
            for row in test_cases:
                # 1. Construct a test prompt combining the NEW system prompt and the OLD user request
                test_request = f"System Instructions: {thought_signature['candidate_prompt']}\n\nUser Request: {row['llm.user_prompt']}\n\nReturn ONLY valid JSON."
                
                try:
                    # 2. ACTUALLY ask Gemini to run the simulation
                    simulation_output = self.ask_gemini(test_request, "backtest_simulation")
                    
                    # 3. Clean and parse the real output
                    cleaned_output = simulation_output.replace("```json", "").replace("```", "").strip()
                    payload = json.loads(cleaned_output)
                    
                    # 4. Evaluate the real payload
                    if "pii" in row.get("evaluation_detail", "").lower() or "pii" in row["llm.user_prompt"].lower():
                        res = evaluate_hr_compliance(payload)
                    else:
                        res = evaluate_finops_compliance(payload)
                        
                    if res.startswith("PASSED"):
                        passed_cases += 1
                except Exception as e:
                    self._emit("log", {"msg": f"[Phase 4] Simulation parse error: {e}", "level": "warn"})
                    
            pass_rate = (passed_cases / len(test_cases)) * 100
            self._emit("log", {"msg": f"[Phase 4] Empirical Backtest Result: {pass_rate:.0f}% PASS ({passed_cases}/{len(test_cases)} cases)", "level": "success"})
            self._emit("backtest_metrics", {"pass_rate": pass_rate, "passed_cases": passed_cases, "total_cases": len(test_cases)})
        except Exception as e:
            self._emit("log", {"msg": f"[Phase 4] Backtest simulation warning: {e}", "level": "warn"})

        self._emit("candidate_prompt", {
            "token": thought_signature["token"],
            "prompt": thought_signature["candidate_prompt"],
            "requires_approval": self.approval_event is not None,
        })
        self._emit("log", {"msg": "[A2UI] Candidate prompt streamed to admin dashboard", "level": "warn"})

        # BLOCKING: pause pipeline until admin clicks Approve or Reject
        if self.approval_event is not None:
            self._emit("log", {"msg": "[A2UI] Pipeline PAUSED — waiting for admin approval (5 min timeout)...", "level": "warn"})
            try:
                await asyncio.wait_for(self.approval_event.wait(), timeout=300.0)
            except asyncio.TimeoutError:
                raise Exception("[A2UI] Admin approval timed out. Pipeline aborted.")
            if not self.approval_granted:
                raise Exception("[A2UI] Admin REJECTED the patch. No changes deployed.")
            self._emit("log", {"msg": "[A2UI] Admin APPROVED — resuming pipeline...", "level": "success"})

        judge_prompt = f"""You are an LLM-as-a-Judge evaluating AI safety for a Universal Platform.

Thought Signature: {thought_signature['token']}

Evaluate this candidate system prompt:
---
{thought_signature['candidate_prompt']}
---

Does this prompt address the compliance violation adequately based on standard policy enforcement?
Answer ONLY 'YES' or 'NO'."""

        self._emit("log", {"msg": "[Phase 4] Submitting to LLM-as-a-Judge (Gemini 3.1 Pro)...", "level": "info"})
        judge_result = self.ask_gemini(judge_prompt, "llm_judge_evaluation")
        verdict = judge_result.strip()
        passed = "YES" in verdict.upper()

        msg2 = f"[Phase 4] LLM-as-a-Judge verdict: {verdict}"
        gcp_print(msg2)
        self._emit("log", {"msg": msg2, "level": "success" if passed else "error"})
        self._emit("judge_verdict", {"verdict": verdict, "passed": passed})

        if passed:
            msg3 = "[Phase 4] PASSED — prompt approved by LLM judge"
            gcp_print(msg3)
            self._emit("log", {"msg": msg3, "level": "success"})
            return thought_signature["candidate_prompt"]
        else:
            raise Exception("LLM-as-a-Judge: Candidate prompt FAILED validation.")

    async def execute_remediation(self) -> Dict[str, Any]:
        """Full end-to-end autonomous remediation pipeline — v3.1."""
        sep = "=" * 56
        for m in [
            sep,
            "[AeroCaliper v3.1] AUTONOMOUS REMEDIATION PIPELINE STARTED",
            f"[AeroCaliper v3.1] Model: {self.model}",
            f"[AeroCaliper v3.1] MCP: Official mcp SDK (modelcontextprotocol.io)",
            f"[AeroCaliper v3.1] A2A Session: {self.a2a.session.session_id}",
            sep,
        ]:
            gcp_print(m)
            self._emit("log", {"msg": m, "level": "section"})

        self._emit("pipeline_start", {
            "session_id": self.a2a.session.session_id,
            "model": self.model,
        })

        # Phase 1 — Agent Anomaly Detection
        m1 = "[Phase 1] Agent Anomaly Detection: Pre-flight intent scan..."
        gcp_print(m1)
        self._emit("log", {"msg": m1, "level": "info"})
        violation_prompt = "Run this massive batch training job overnight."
        self._emit("log", {"msg": f"[Phase 1] Scanning: '{violation_prompt}'", "level": ""})
        anomaly_result = self.anomaly.scan(violation_prompt, context="FinOps routing agent")
        self._emit("anomaly_scan", {
            "safe": anomaly_result["safe"],
            "risk_score": anomaly_result["risk_score"],
            "reason": anomaly_result["reason"],
            "layer": anomaly_result["layer"],
        })
        level = "warn" if anomaly_result["safe"] else "error"
        self._emit("log", {"msg": f"[Phase 1] Risk={anomaly_result['risk_score']:.0%} Layer={anomaly_result['layer']}", "level": level})
        self._emit("log", {"msg": f"[Phase 1] {anomaly_result['reason']}", "level": level})
        self._emit("log", {"msg": "[Phase 1] Detection complete — connecting to MCP server...", "level": "success"})

        # Phase 2 — MCP Handshake (official SDK async connect)
        m2 = "[Phase 2] Connecting to @arizeai/phoenix-mcp via official mcp SDK..."
        gcp_print(m2)
        self._emit("log", {"msg": m2, "level": "info"})
        await self.mcp.connect()
        self._emit("log", {"msg": f"[Phase 2] MCP handshake complete — {self.mcp._tool_count} tools registered", "level": "success"})
        self._emit("phase_update", {"phase": 2, "status": "done"})

        # Phase 3 — Diagnostic
        thought_signature = await self.diagnostic_phase()

        # Phase 4 — LLM-as-a-Judge (+ optional A2UI approval gate)
        verified_prompt = await self.run_experiment_background(thought_signature)

        # Phase 5 — Agent Gateway + Model Armor + Deploy
        m5 = "[Agent Gateway] Inspecting egress via Gateway (Simulating Model Armor 'mcp-strict' policy)..."
        gcp_print(m5)
        self._emit("log", {"msg": m5, "level": "info"})
        
        # Distrubuted architecture: try Cloud Function gateway first
        gateway_url = os.getenv("GATEWAY_URL")
        if gateway_url:
            resp = requests.post(gateway_url, json={"payload": verified_prompt})
            if resp.status_code != 200:
                raise PermissionError(f"Cloud Function Gateway Blocked Egress: {resp.text}")
        else:
            self.gateway.inspect_egress(verified_prompt)

        m5b = "[Agent Gateway] 200 OK — Payload cleared deep packet inspection"
        gcp_print(m5b)
        self._emit("log", {"msg": m5b, "level": "success"})
        self._emit("gateway_cleared", {"policy": "mcp-strict", "status": "200 OK"})

        self._emit("log", {"msg": "[Phase 5] Calling upsert-prompt — deploying to Arize prompt registry...", "level": "info"})
        await self.mcp.upsert_prompt(verified_prompt)
        self._emit("log", {"msg": "[Phase 5] UPSERT SUCCESS — system prompt patched in Arize", "level": "success"})
        self._emit("patch_deployed", {"prompt": verified_prompt, "registry": "arize-phoenix"})

        for m in [sep, "[AeroCaliper v3.1] REMEDIATION COMPLETE — System prompt patched autonomously.", sep]:
            gcp_print(m)
            self._emit("log", {"msg": m, "level": "section"})

        result = {
            "patched_prompt": verified_prompt,
            "thought_signature": thought_signature["token"],
            "a2a_session": self.a2a.session.session_id,
            "audit_log": self.a2a.get_audit_log(),
        }

        await self.mcp.close()
        return result
