import os
import json
import asyncio
from contextlib import AsyncExitStack

# Official MCP Python SDK (from Anthropic / modelcontextprotocol.io)
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

def gcp_print(msg):
    print(msg)

class StandardMCPClient:
    """
    Enterprise-grade MCP client using the OFFICIAL mcp Python SDK.
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
        space_name = env_vars.get("ARIZE_SPACE_NAME", env_vars.get("ARIZE_SPACE_ID", ""))
        base_url = f"https://app.phoenix.arize.com/s/{space_name}" if space_name else "https://app.phoenix.arize.com"
        
        if arize_key:
            env_vars["PHOENIX_CLIENT_HEADERS"] = f"api_key={arize_key}"
            env_vars["PHOENIX_COLLECTOR_ENDPOINT"] = base_url
            env_vars["PHOENIX_HOST"] = "https://app.phoenix.arize.com"

        server_params = StdioServerParameters(
            command="cmd.exe" if os.name == "nt" else "npx",
            args=(
                ["/c", "npx", "-y", "@arizeai/phoenix-mcp", "--project", "aerocaliper", "--baseUrl", base_url, "--apiKey", arize_key]
                if os.name == "nt"
                else ["-y", "@arizeai/phoenix-mcp", "--project", "aerocaliper", "--baseUrl", base_url, "--apiKey", arize_key]
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

        async def log_progress():
            try:
                for i in range(1, 20):
                    await asyncio.sleep(5)
                    self._emit("log", {"msg": f"[Phase 3] Still querying Arize Phoenix MCP... ({i*5}s elapsed)", "level": "info"})
            except asyncio.CancelledError:
                pass

        progress_task = asyncio.create_task(log_progress())

        try:
            # We fetch 5 spans now instead of 1, as required by the spec
            result = await self.session.call_tool("get-spans", arguments={"project_identifier": "aerocaliper", "limit": 5})

            if result.isError or not result.content:
                return self._canonical_fallback("MCP tool returned error or empty content")

            raw = result.content[0].text
            if not raw or raw.strip() in ("fetch failed", "null", "[]", "{}"):
                return self._canonical_fallback(f"empty response: {raw!r}")

            parsed = json.loads(raw)
            # Handle list response or dict wrapper
            if isinstance(parsed, dict) and "spans" in parsed:
                parsed = parsed["spans"]
            if isinstance(parsed, list):
                if not parsed:
                    return self._canonical_fallback("empty spans list")
                # Filter for explicit failures
                failed_spans = [s for s in parsed if str(s).find('POLICY VIOLATION') != -1 or 'failed' in str(s).lower() or 'error' in str(s).lower() or s.get('status', {}).get('code') == 'ERROR']
                if failed_spans:
                    parsed = failed_spans[0] # Return the most recent failed span
                else:
                    parsed = parsed[0]

            # trace_id is nested inside context for MCP v1 format
            context_dict = parsed.get("context", {})
            trace_id = (
                context_dict.get('trace_id') or context_dict.get('traceId') or
                parsed.get('traceId') or parsed.get('trace_id') or
                parsed.get('id') or 'unknown'
            )
            parsed['trace_id'] = trace_id
            msg = f"[MCP] Live span retrieved: trace_id={trace_id}"
            gcp_print(msg)
            self._emit("log", {"msg": msg, "level": "success"})
            return parsed

        except Exception as e:
            return self._canonical_fallback(f"exception: {e}")
        finally:
            progress_task.cancel()

    def _canonical_fallback(self, reason: str) -> dict:
        raise RuntimeError(f"[MCP] Strict Mode: Trace fetching failed. Reason: {reason}")

    async def upsert_prompt(self, new_prompt: str, target_use_case: str = "finops") -> bool:
        if not self.session:
            await self.connect()

        result = await self.session.call_tool(
            "upsert-prompt",
            arguments={
                "name": f"aerocaliper{target_use_case}routingagent",
                "template": new_prompt,
                "description": f"AeroCaliper autonomous remediation patch ({target_use_case} domain)",
                "model_provider": "GOOGLE",
                "model_name": "gemini-3.1-pro-preview",
                "temperature": 0.0,
            },
        )

        if result.isError or result.content:
            raw_text = ""
            if result.content:
                try:
                    raw_text = result.content[0].text if hasattr(result.content[0], "text") else str(result.content[0])
                except Exception:
                    raw_text = str(result.content)

            if "fetch failed" in raw_text.lower() or "500" in raw_text:
                raise RuntimeError("Strict Mode: MCP upsert-prompt tool failed due to 'fetch failed' (Arize Cloud endpoint unreachable) or 500 Internal Server Error.")
            elif result.isError:
                raise Exception(f"MCP upsert-prompt protocol error: {result.content}")
            else:
                self._emit("log", {"msg": f"[MCP UPSERT OUTPUT]: {raw_text}", "level": "warn"})

        msg = "[MCP] UPSERT SUCCESS — patched prompt deployed to Arize prompt registry."
        gcp_print(msg)
        self._emit("log", {"msg": msg, "level": "success"})
        return True

    async def close(self) -> None:
        await self.exit_stack.aclose()
