import asyncio
from aerocaliper import AeroCaliperAgent

async def run():
    agent = AeroCaliperAgent()
    print(await agent.execute_remediation())

if __name__ == "__main__":
    asyncio.run(run())
