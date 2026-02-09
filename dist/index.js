#!/usr/bin/env node
import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { CallToolRequestSchema, ListToolsRequestSchema, } from '@modelcontextprotocol/sdk/types.js';
import { tools } from './toolDefinitions.js';
import { getVerse, getSurah, listSurahs, searchVerses } from './tools/quran.js';
import { searchClaims, getClaimEvidence, getClaimDependencies, listPatterns, saveInsight, getClaim, deleteClaim, deleteMultipleClaims, getVerseClaims, getClaimStats, saveBulkInsights, updateClaim, findRelatedClaims, addClaimDependency, deletePattern } from './tools/research.js';
import { searchByLinguisticFeatures, createPatternInterpretation, createSurahTheme, addVerseEvidence } from './tools/linguistic.js';
import { startWorkflowSession, getNextVerseInWorkflow, submitVerification, getWorkflowStats, listWorkflowSessions, checkAndTransitionPhase } from './tools/workflow.js';
import { getVerseWithContext } from './tools/context.js';
import { closeDatabase } from './db.js';
import { jsonResponse, errorResponse } from './utils/dbHelpers.js';
// Tool handlers - each returns data, serialization is handled by the dispatch wrapper
const handlers = {
    get_verse: async (args) => {
        const verse = await getVerse(args.surah, args.ayah);
        if (!verse)
            return { error: `Verse ${args.surah}:${args.ayah} not found` };
        return verse;
    },
    get_surah: async (args) => {
        const result = await getSurah(args.surah);
        if (!result)
            return { error: `Surah ${args.surah} not found` };
        return result;
    },
    list_surahs: async () => {
        return await listSurahs();
    },
    search_verses: async (args) => {
        return await searchVerses(args.query, args.limit);
    },
    search_claims: async (args) => {
        return await searchClaims(args);
    },
    get_claim: async (args) => {
        const claim = await getClaim(args.claim_id);
        if (!claim)
            return { error: `Claim ${args.claim_id} not found` };
        return claim;
    },
    get_claim_evidence: async (args) => {
        return await getClaimEvidence(args.claim_id);
    },
    get_claim_dependencies: async (args) => {
        return await getClaimDependencies(args.claim_id);
    },
    list_patterns: async (args) => {
        return await listPatterns(args.pattern_type);
    },
    save_insight: async (args) => {
        return await saveInsight(args);
    },
    search_by_linguistic_features: async (args) => {
        return await searchByLinguisticFeatures(args);
    },
    create_pattern_interpretation: async (args) => {
        return await createPatternInterpretation(args);
    },
    create_surah_theme: async (args) => {
        return await createSurahTheme(args);
    },
    add_verse_evidence: async (args) => {
        return await addVerseEvidence(args);
    },
    start_workflow_session: async (args) => {
        return await startWorkflowSession(args);
    },
    get_next_verse: async (args) => {
        return await getNextVerseInWorkflow(args.session_id);
    },
    submit_verification: async (args) => {
        return await submitVerification(args);
    },
    get_workflow_stats: async (args) => {
        return await getWorkflowStats(args.session_id);
    },
    list_workflow_sessions: async (args) => {
        return await listWorkflowSessions(args);
    },
    check_phase_transition: async (args) => {
        return await checkAndTransitionPhase(args.session_id);
    },
    delete_claim: async (args) => {
        return await deleteClaim(args.claim_id);
    },
    delete_multiple_claims: async (args) => {
        return await deleteMultipleClaims(args.claim_ids);
    },
    get_claim_stats: async () => {
        return await getClaimStats();
    },
    save_bulk_insights: async (args) => {
        return await saveBulkInsights(args);
    },
    update_claim: async (args) => {
        return await updateClaim(args);
    },
    get_verse_claims: async (args) => {
        return await getVerseClaims(args.surah, args.ayah);
    },
    get_verse_with_context: async (args) => {
        return await getVerseWithContext(args.surah, args.ayah, {
            include_root_claims: args.include_root_claims ?? true,
            include_form_claims: args.include_form_claims ?? true,
            include_pos_claims: args.include_pos_claims ?? true
        });
    },
    find_related_claims: async (args) => {
        return await findRelatedClaims(args.claim_id, args.limit);
    },
    add_claim_dependency: async (args) => {
        return await addClaimDependency(args);
    },
    delete_pattern: async (args) => {
        return await deletePattern(args.pattern_id);
    }
};
// Create MCP server
const server = new Server({ name: 'kalima-mcp-server', version: '1.0.0' }, { capabilities: { tools: {} } });
// Handle tool list requests
server.setRequestHandler(ListToolsRequestSchema, async () => {
    return { tools };
});
// Handle tool execution via handler map
server.setRequestHandler(CallToolRequestSchema, async (request) => {
    const { name, arguments: args } = request.params;
    const handler = handlers[name];
    if (!handler) {
        return errorResponse(`Unknown tool: ${name}`);
    }
    try {
        const result = await handler(args ?? {});
        return jsonResponse(result);
    }
    catch (error) {
        return errorResponse(`Error executing ${name}: ${error}`);
    }
});
// Cleanup on exit
process.on('SIGINT', () => {
    closeDatabase();
    process.exit(0);
});
process.on('SIGTERM', () => {
    closeDatabase();
    process.exit(0);
});
// Start server
async function main() {
    const transport = new StdioServerTransport();
    await server.connect(transport);
    console.error('Kalima MCP server running on stdio');
}
main().catch((error) => {
    console.error('Server error:', error);
    process.exit(1);
});
//# sourceMappingURL=index.js.map