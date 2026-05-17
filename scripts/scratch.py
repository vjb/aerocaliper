import asyncio
import os
from aerocaliper import AeroCaliperAgent

async def run_cli_test():
    print("=== STARTING CLI PIPELINE TEST ===")
    agent = AeroCaliperAgent()
    try:
        result = await agent.execute_remediation()
        print("\n=== PIPELINE SUCCESS ===")
        print("Patched Prompt:")
        print(result["patched_prompt"])
    except Exception as e:
        print("\n=== PIPELINE FAILED ===")
        import traceback
        print(traceback.format_exc())

if __name__ == "__main__":
    asyncio.run(run_cli_test())
