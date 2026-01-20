// Quick test script to verify MCP server functions work
import { getVerse, getSurah, listSurahs } from './dist/tools/quran.js';
import { searchClaims } from './dist/tools/research.js';

async function test() {
  console.log('Testing Kalima MCP Server...\n');

  try {
    // Test 1: Get a verse (Al-Fatiha 1:1)
    console.log('Test 1: Getting verse 1:1...');
    const verse = await getVerse(1, 1);
    console.log('Result:', verse);
    console.log('✓ Verse query works\n');

    // Test 2: List surahs (first 5)
    console.log('Test 2: Listing first 5 surahs...');
    const surahs = await listSurahs();
    console.log('Found', surahs.length, 'surahs');
    console.log('First 5:', surahs.slice(0, 5));
    console.log('✓ List surahs works\n');

    // Test 3: Search claims
    console.log('Test 3: Searching claims in hypothesis phase...');
    const claims = await searchClaims({ phase: 'hypothesis', limit: 5 });
    console.log('Found', claims.length, 'claims');
    if (claims.length > 0) {
      console.log('First claim:', claims[0].content.substring(0, 100) + '...');
    }
    console.log('✓ Search claims works\n');

    console.log('All tests passed! MCP server is ready.');
  } catch (error) {
    console.error('Test failed:', error);
    process.exit(1);
  }
}

test();
