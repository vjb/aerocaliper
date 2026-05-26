import asyncio
import threading
from mcp_client import StandardMCPClient

def _run_in_new_thread(coro):
    result = None
    exception = None

    def target():
        nonlocal result, exception
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(coro)
            loop.close()
        except Exception as e:
            exception = e

    thread = threading.Thread(target=target)
    thread.start()
    thread.join()

    if exception:
        raise exception
    return result

def fetch_failed_traces() -> dict:
    """
    Fetch the most recent failed execution traces from the Arize Phoenix MCP server.
    Returns a structured dictionary representing the failed span.
    """
    async def _run():
        client = StandardMCPClient()
        try:
            return await client.get_failed_spans()
        finally:
            await client.close()

    return _run_in_new_thread(_run())

def deploy_prompt_patch(patched_prompt: str, domain: str) -> str:
    """
    Deploys a patched system prompt back to the Arize Prompt Registry via the MCP server.
    """
    async def _run():
        client = StandardMCPClient()
        try:
            success = await client.upsert_prompt(patched_prompt, target_use_case=domain)
            if success:
                return "SUCCESS: Prompt successfully deployed to Arize Prompt Registry."
            return "FAILURE"
        finally:
            await client.close()
    
    return _run_in_new_thread(_run())

