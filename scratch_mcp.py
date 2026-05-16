import asyncio, os, json
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def test_mcp():
    env = os.environ.copy()
    key = env.get('PHOENIX_API_KEY', '')
    env['PHOENIX_API_KEY'] = key
    env['PHOENIX_CLIENT_HEADERS'] = f'authorization=Bearer {key}'
    
    params = StdioServerParameters(command='npx', args=['-y', '@arizeai/phoenix-mcp'], env=env)
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            print('Initialized. Fetching spans...')
            try:
                res = await session.call_tool('get-spans', arguments={'project_identifier': 'aerocaliper', 'limit': 1})
                print('Result:', res)
            except Exception as e:
                print('Error:', e)

asyncio.run(test_mcp())
