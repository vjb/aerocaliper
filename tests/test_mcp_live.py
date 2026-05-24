import os
import sys
import pytest
from dotenv import load_dotenv
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from aerocaliper import StandardMCPClient

load_dotenv()

@pytest.mark.asyncio
async def test_mcp_live():
    print("Testing Arize Phoenix MCP Integration...")
    client = StandardMCPClient()
    try:
        await client.connect()
        # Test fetching span
        span = await client.get_failed_spans()
        print(f"PASS: span retrieved: {span}")
        assert span is not None
    except Exception as e:
        pytest.fail(f"FAIL: MCP connection or span fetch failed: {e}")
    finally:
        await client.close()

