import asyncio
from mcp.client.stdio import StdioClient

async def test():
    async with StdioClient() as client:
        result = await client.call_tool('get_verse_with_context', {'surah': 1, 'ayah': 1})
        print('get_verse_with_context:', 'OK' if result.content else 'FAIL')
        
        result = await client.call_tool('compare_with_traditional', {'surah': 1, 'ayah': 1})
        print('compare_with_traditional:', 'OK' if result.content else 'FAIL')
        
        result = await client.call_tool('detect_boundaries', {'surah': 1, 'start_ayah': 1, 'end_ayah': 3})
        print('detect_boundaries:', 'OK' if result.content else 'FAIL')
        
        result = await client.call_tool('analyze_verse_emphasis', {'surah': 1, 'ayah': 1})
        print('analyze_verse_emphasis:', 'OK' if result.content else 'FAIL')

asyncio.run(test())