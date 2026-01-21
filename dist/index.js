#!/usr/bin/env node
import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { CallToolRequestSchema, ListToolsRequestSchema, } from '@modelcontextprotocol/sdk/types.js';
import { getVerse, getSurah, listSurahs, searchVerses } from './tools/quran.js';
import { searchClaims, getClaimEvidence, getClaimDependencies, listPatterns, saveInsight, updateClaimPhase, deleteClaim, deleteMultipleClaims } from './tools/research.js';
import { searchByLinguisticFeatures, createPatternInterpretation, createSurahTheme, addVerseEvidence } from './tools/linguistic.js';
import { startWorkflowSession, getNextVerseInWorkflow, submitVerification, getWorkflowStats, listWorkflowSessions, checkAndTransitionPhase } from './tools/workflow.js';
import { closeDatabase } from './db.js';
// Define all available tools
const tools = [
    {
        name: 'get_verse',
        description: 'Retrieve a specific verse from the Quran with its Arabic text. Use this when the user asks about a specific verse (e.g., "Show me verse 2:255").',
        inputSchema: {
            type: 'object',
            properties: {
                surah: {
                    type: 'number',
                    description: 'The surah (chapter) number (1-114)',
                    minimum: 1,
                    maximum: 114
                },
                ayah: {
                    type: 'number',
                    description: 'The ayah (verse) number within the surah',
                    minimum: 1
                }
            },
            required: ['surah', 'ayah']
        }
    },
    {
        name: 'get_surah',
        description: 'Retrieve an entire surah (chapter) with all its verses. Use this when the user asks about a full chapter (e.g., "Show me Surah Al-Fatiha").',
        inputSchema: {
            type: 'object',
            properties: {
                surah: {
                    type: 'number',
                    description: 'The surah (chapter) number (1-114)',
                    minimum: 1,
                    maximum: 114
                }
            },
            required: ['surah']
        }
    },
    {
        name: 'list_surahs',
        description: 'Get a list of all 114 surahs with their Arabic names and verse counts. Use this when the user wants to browse chapters or know chapter names.',
        inputSchema: {
            type: 'object',
            properties: {},
            required: []
        }
    },
    {
        name: 'search_verses',
        description: 'Search for verses containing specific Arabic text. Use this for finding verses with particular words or phrases.',
        inputSchema: {
            type: 'object',
            properties: {
                query: {
                    type: 'string',
                    description: 'Arabic text to search for'
                },
                limit: {
                    type: 'number',
                    description: 'Maximum number of results (default: 20)',
                    minimum: 1,
                    maximum: 100
                }
            },
            required: ['query']
        }
    },
    {
        name: 'search_claims',
        description: 'Search research claims in the database. Claims are hypotheses or observations about the Quran being verified through falsification methodology.',
        inputSchema: {
            type: 'object',
            properties: {
                phase: {
                    type: 'string',
                    description: 'Filter by research phase',
                    enum: ['question', 'hypothesis', 'validation', 'active_verification', 'passive_verification']
                },
                pattern_id: {
                    type: 'string',
                    description: 'Filter by pattern ID if looking for claims related to a specific pattern'
                },
                limit: {
                    type: 'number',
                    description: 'Maximum number of results (default: 50)',
                    minimum: 1,
                    maximum: 200
                }
            },
            required: []
        }
    },
    {
        name: 'get_claim_evidence',
        description: 'Get all evidence (verse references) supporting a specific research claim.',
        inputSchema: {
            type: 'object',
            properties: {
                claim_id: {
                    type: 'string',
                    description: 'The unique identifier of the claim'
                }
            },
            required: ['claim_id']
        }
    },
    {
        name: 'get_claim_dependencies',
        description: 'Get the dependency tree for a claim - which other claims it depends on or relates to.',
        inputSchema: {
            type: 'object',
            properties: {
                claim_id: {
                    type: 'string',
                    description: 'The unique identifier of the claim'
                }
            },
            required: ['claim_id']
        }
    },
    {
        name: 'list_patterns',
        description: 'List morphological, syntactic, or semantic patterns identified in the Quran.',
        inputSchema: {
            type: 'object',
            properties: {
                pattern_type: {
                    type: 'string',
                    description: 'Filter by pattern type',
                    enum: ['morphological', 'syntactic', 'semantic']
                }
            },
            required: []
        }
    },
    {
        name: 'save_insight',
        description: 'Save a new research claim or insight discovered during conversation. Use this to preserve important observations for future research.',
        inputSchema: {
            type: 'object',
            properties: {
                content: {
                    type: 'string',
                    description: 'The claim or insight text'
                },
                phase: {
                    type: 'string',
                    description: 'Current research phase (default: question)',
                    enum: ['question', 'hypothesis', 'validation'],
                    default: 'question'
                },
                pattern_id: {
                    type: 'string',
                    description: 'Optional pattern ID this claim relates to'
                },
                evidence_verses: {
                    type: 'array',
                    description: 'Array of verse references as evidence',
                    items: {
                        type: 'object',
                        properties: {
                            surah: { type: 'number' },
                            ayah: { type: 'number' },
                            notes: { type: 'string' }
                        },
                        required: ['surah', 'ayah']
                    }
                }
            },
            required: ['content']
        }
    },
    {
        name: 'update_claim_phase',
        description: 'Update the phase of an existing claim as research progresses through the falsification methodology.',
        inputSchema: {
            type: 'object',
            properties: {
                claim_id: {
                    type: 'string',
                    description: 'The claim ID to update'
                },
                new_phase: {
                    type: 'string',
                    description: 'The new research phase',
                    enum: ['question', 'hypothesis', 'validation', 'active_verification', 'passive_verification']
                }
            },
            required: ['claim_id', 'new_phase']
        }
    },
    {
        name: 'search_by_linguistic_features',
        description: 'Search verses by linguistic features like part of speech, verb form, mood, aspect, root, etc. Use this for linguistic analysis like finding all present tense verbs, imperatives, or words from a specific root.',
        inputSchema: {
            type: 'object',
            properties: {
                pos: {
                    type: 'string',
                    description: 'Part of speech (e.g., "VERB", "NOUN", "ADJ", "PRON")'
                },
                aspect: {
                    type: 'string',
                    description: 'Verb aspect: "imperfective" (present tense) or "perfective" (past tense)'
                },
                mood: {
                    type: 'string',
                    description: 'Verb mood: "indicative", "subjunctive", "imperative", "jussive"'
                },
                verb_form: {
                    type: 'string',
                    description: 'Specific verb form'
                },
                voice: {
                    type: 'string',
                    description: 'Voice: "active" or "passive"'
                },
                person: {
                    type: 'string',
                    description: 'Grammatical person: "1st", "2nd", "3rd"'
                },
                number: {
                    type: 'string',
                    description: 'Number: "singular", "dual", "plural"'
                },
                gender: {
                    type: 'string',
                    description: 'Gender: "masculine", "feminine"'
                },
                root: {
                    type: 'string',
                    description: 'Arabic root (e.g., "ق-و-ل" for speech/saying)'
                },
                lemma: {
                    type: 'string',
                    description: 'Base word form'
                },
                case_value: {
                    type: 'string',
                    description: 'Grammatical case: "nominative", "accusative", "genitive"'
                },
                dependency_rel: {
                    type: 'string',
                    description: 'Syntactic dependency relation'
                },
                role: {
                    type: 'string',
                    description: 'Grammatical role in sentence'
                },
                surah: {
                    type: 'number',
                    description: 'Limit search to specific surah',
                    minimum: 1,
                    maximum: 114
                },
                limit: {
                    type: 'number',
                    description: 'Maximum number of results (default: 50)',
                    minimum: 1,
                    maximum: 200,
                    default: 50
                }
            },
            required: []
        }
    },
    {
        name: 'create_pattern_interpretation',
        description: 'Create a linguistic pattern with interpretation. Use this to document observations like "present tense verbs indicate ongoing or future actions".',
        inputSchema: {
            type: 'object',
            properties: {
                description: {
                    type: 'string',
                    description: 'Description of the pattern (e.g., "Present tense verbs in the Quran")'
                },
                pattern_type: {
                    type: 'string',
                    description: 'Type of pattern',
                    enum: ['morphological', 'syntactic', 'semantic']
                },
                interpretation: {
                    type: 'string',
                    description: 'The interpretation or meaning of this pattern'
                },
                linguistic_features: {
                    type: 'object',
                    description: 'The linguistic features that define this pattern (e.g., {pos: "VERB", aspect: "imperfective"})'
                },
                scope: {
                    type: 'string',
                    description: 'Scope of the pattern (default: "all_verses")',
                    default: 'all_verses'
                },
                phase: {
                    type: 'string',
                    description: 'Research phase (default: "hypothesis")',
                    enum: ['question', 'hypothesis', 'validation', 'verification'],
                    default: 'hypothesis'
                }
            },
            required: ['description', 'pattern_type', 'interpretation']
        }
    },
    {
        name: 'create_surah_theme',
        description: 'Create a thematic interpretation for an entire surah. Use this to document the main theme or purpose of a chapter.',
        inputSchema: {
            type: 'object',
            properties: {
                surah: {
                    type: 'number',
                    description: 'The surah number (1-114)',
                    minimum: 1,
                    maximum: 114
                },
                theme: {
                    type: 'string',
                    description: 'The main theme of the surah'
                },
                description: {
                    type: 'string',
                    description: 'Additional description or details about the theme'
                },
                phase: {
                    type: 'string',
                    description: 'Research phase (default: "hypothesis")',
                    enum: ['question', 'hypothesis', 'validation', 'verification'],
                    default: 'hypothesis'
                }
            },
            required: ['surah', 'theme']
        }
    },
    {
        name: 'add_verse_evidence',
        description: 'Add a verse as evidence for a claim with verification status. Use this when verifying whether a verse supports, contradicts, or is unclear about a hypothesis.',
        inputSchema: {
            type: 'object',
            properties: {
                claim_id: {
                    type: 'string',
                    description: 'The claim or pattern ID this evidence relates to'
                },
                surah: {
                    type: 'number',
                    description: 'The surah number',
                    minimum: 1,
                    maximum: 114
                },
                ayah: {
                    type: 'number',
                    description: 'The ayah number',
                    minimum: 1
                },
                verification: {
                    type: 'string',
                    description: 'Verification result',
                    enum: ['supports', 'contradicts', 'unclear']
                },
                notes: {
                    type: 'string',
                    description: 'Optional notes about this verification'
                }
            },
            required: ['claim_id', 'surah', 'ayah', 'verification']
        }
    },
    {
        name: 'start_workflow_session',
        description: 'Start a new verification workflow session to systematically verify verses one by one. Use this to begin a structured verification process for a linguistic pattern or surah theme.',
        inputSchema: {
            type: 'object',
            properties: {
                claim_id: {
                    type: 'string',
                    description: 'The claim or pattern ID to verify'
                },
                workflow_type: {
                    type: 'string',
                    description: 'Type of workflow',
                    enum: ['pattern', 'surah_theme']
                },
                linguistic_features: {
                    type: 'object',
                    description: 'For pattern workflow: the linguistic features to search (e.g., {pos: "VERB", aspect: "imperfective"})'
                },
                surah: {
                    type: 'number',
                    description: 'For surah_theme workflow: the surah number to verify',
                    minimum: 1,
                    maximum: 114
                },
                limit: {
                    type: 'number',
                    description: 'For pattern workflow: maximum number of verses (default: 100)',
                    minimum: 1,
                    maximum: 500,
                    default: 100
                }
            },
            required: ['claim_id', 'workflow_type']
        }
    },
    {
        name: 'get_next_verse',
        description: 'Get the next verse in an active workflow session for verification. Returns the verse text, progress, and completion status.',
        inputSchema: {
            type: 'object',
            properties: {
                session_id: {
                    type: 'string',
                    description: 'The workflow session ID'
                }
            },
            required: ['session_id']
        }
    },
    {
        name: 'submit_verification',
        description: 'Submit verification for the current verse in a workflow and advance to the next verse. Saves the verification result and automatically returns the next verse.',
        inputSchema: {
            type: 'object',
            properties: {
                session_id: {
                    type: 'string',
                    description: 'The workflow session ID'
                },
                verification: {
                    type: 'string',
                    description: 'Verification result for current verse',
                    enum: ['supports', 'contradicts', 'unclear']
                },
                notes: {
                    type: 'string',
                    description: 'Optional notes about this verification'
                }
            },
            required: ['session_id', 'verification']
        }
    },
    {
        name: 'get_workflow_stats',
        description: 'Get statistics and progress for a workflow session. Shows total verses, verified count, remaining, and verification breakdown (supports/contradicts/unclear).',
        inputSchema: {
            type: 'object',
            properties: {
                session_id: {
                    type: 'string',
                    description: 'The workflow session ID'
                }
            },
            required: ['session_id']
        }
    },
    {
        name: 'list_workflow_sessions',
        description: 'IMPORTANT: ALWAYS use this MCP tool to list workflow sessions. DO NOT use Bash/SQL commands to query the database directly. This tool lists all workflow sessions with their status and progress. Can filter by status (active/completed/paused). Example: To see all active sessions, call this tool with status: "active". Returns session_id, claim_id, progress, etc.',
        inputSchema: {
            type: 'object',
            properties: {
                status: {
                    type: 'string',
                    description: 'Optional status filter',
                    enum: ['active', 'completed', 'paused']
                }
            },
            required: []
        }
    },
    {
        name: 'check_phase_transition',
        description: 'Check if a claim should transition to a new research phase based on verification results. Auto-transitions to "rejected" if contradictions found, or "validated" if sufficient supporting evidence.',
        inputSchema: {
            type: 'object',
            properties: {
                session_id: {
                    type: 'string',
                    description: 'The workflow session ID'
                }
            },
            required: ['session_id']
        }
    },
    {
        name: 'delete_claim',
        description: 'IMPORTANT: ALWAYS use this MCP tool to delete claims. DO NOT use Bash commands with SQL queries (e.g., node -e "db.exec(...)"). This tool safely deletes a claim and its associated evidence from the database. Example: To delete claim_123, call this tool with claim_id: "claim_123". Automatically handles foreign key constraints and cascading deletions.',
        inputSchema: {
            type: 'object',
            properties: {
                claim_id: {
                    type: 'string',
                    description: 'The claim ID to delete (format: claim_123)'
                }
            },
            required: ['claim_id']
        }
    },
    {
        name: 'delete_multiple_claims',
        description: 'Delete multiple claims at once. Use for cleaning up test/duplicate entries.',
        inputSchema: {
            type: 'object',
            properties: {
                claim_ids: {
                    type: 'array',
                    description: 'Array of claim IDs to delete',
                    items: { type: 'string' }
                }
            },
            required: ['claim_ids']
        }
    }
];
// Create MCP server
const server = new Server({
    name: 'kalima-mcp-server',
    version: '1.0.0',
}, {
    capabilities: {
        tools: {},
    },
});
// Handle tool list requests
server.setRequestHandler(ListToolsRequestSchema, async () => {
    return { tools };
});
// Handle tool execution
server.setRequestHandler(CallToolRequestSchema, async (request) => {
    const { name, arguments: args } = request.params;
    try {
        switch (name) {
            case 'get_verse': {
                const { surah, ayah } = args;
                const verse = await getVerse(surah, ayah);
                if (!verse) {
                    return {
                        content: [{
                                type: 'text',
                                text: `Verse ${surah}:${ayah} not found in database.`
                            }]
                    };
                }
                return {
                    content: [{
                            type: 'text',
                            text: JSON.stringify(verse, null, 2)
                        }]
                };
            }
            case 'get_surah': {
                const { surah } = args;
                const result = await getSurah(surah);
                if (!result) {
                    return {
                        content: [{
                                type: 'text',
                                text: `Surah ${surah} not found in database.`
                            }]
                    };
                }
                return {
                    content: [{
                            type: 'text',
                            text: JSON.stringify(result, null, 2)
                        }]
                };
            }
            case 'list_surahs': {
                const surahs = await listSurahs();
                return {
                    content: [{
                            type: 'text',
                            text: JSON.stringify(surahs, null, 2)
                        }]
                };
            }
            case 'search_verses': {
                const { query, limit } = args;
                const verses = await searchVerses(query, limit);
                return {
                    content: [{
                            type: 'text',
                            text: JSON.stringify(verses, null, 2)
                        }]
                };
            }
            case 'search_claims': {
                const options = args;
                const claims = await searchClaims(options);
                return {
                    content: [{
                            type: 'text',
                            text: JSON.stringify(claims, null, 2)
                        }]
                };
            }
            case 'get_claim_evidence': {
                const { claim_id } = args;
                const evidence = await getClaimEvidence(claim_id);
                return {
                    content: [{
                            type: 'text',
                            text: JSON.stringify(evidence, null, 2)
                        }]
                };
            }
            case 'get_claim_dependencies': {
                const { claim_id } = args;
                const result = await getClaimDependencies(claim_id);
                return {
                    content: [{
                            type: 'text',
                            text: JSON.stringify(result, null, 2)
                        }]
                };
            }
            case 'list_patterns': {
                const { pattern_type } = args;
                const patterns = await listPatterns(pattern_type);
                return {
                    content: [{
                            type: 'text',
                            text: JSON.stringify(patterns, null, 2)
                        }]
                };
            }
            case 'save_insight': {
                const data = args;
                const result = await saveInsight(data);
                return {
                    content: [{
                            type: 'text',
                            text: JSON.stringify(result, null, 2)
                        }]
                };
            }
            case 'update_claim_phase': {
                const { claim_id, new_phase } = args;
                const success = await updateClaimPhase(claim_id, new_phase);
                const message = success
                    ? `Claim ${claim_id} updated to phase: ${new_phase}`
                    : `Failed to update claim ${claim_id}`;
                return {
                    content: [{
                            type: 'text',
                            text: JSON.stringify({ success, message }, null, 2)
                        }]
                };
            }
            case 'search_by_linguistic_features': {
                const options = args;
                const verses = await searchByLinguisticFeatures(options);
                return {
                    content: [{
                            type: 'text',
                            text: JSON.stringify(verses, null, 2)
                        }]
                };
            }
            case 'create_pattern_interpretation': {
                const data = args;
                const result = await createPatternInterpretation(data);
                return {
                    content: [{
                            type: 'text',
                            text: JSON.stringify(result, null, 2)
                        }]
                };
            }
            case 'create_surah_theme': {
                const data = args;
                const result = await createSurahTheme(data);
                return {
                    content: [{
                            type: 'text',
                            text: JSON.stringify(result, null, 2)
                        }]
                };
            }
            case 'add_verse_evidence': {
                const data = args;
                const result = await addVerseEvidence(data);
                return {
                    content: [{
                            type: 'text',
                            text: JSON.stringify(result, null, 2)
                        }]
                };
            }
            case 'start_workflow_session': {
                const data = args;
                const result = await startWorkflowSession(data);
                return {
                    content: [{
                            type: 'text',
                            text: JSON.stringify(result, null, 2)
                        }]
                };
            }
            case 'get_next_verse': {
                const { session_id } = args;
                const result = await getNextVerseInWorkflow(session_id);
                return {
                    content: [{
                            type: 'text',
                            text: JSON.stringify(result, null, 2)
                        }]
                };
            }
            case 'submit_verification': {
                const data = args;
                const result = await submitVerification(data);
                return {
                    content: [{
                            type: 'text',
                            text: JSON.stringify(result, null, 2)
                        }]
                };
            }
            case 'get_workflow_stats': {
                const { session_id } = args;
                const result = await getWorkflowStats(session_id);
                return {
                    content: [{
                            type: 'text',
                            text: JSON.stringify(result, null, 2)
                        }]
                };
            }
            case 'list_workflow_sessions': {
                const data = args;
                const result = await listWorkflowSessions(data);
                return {
                    content: [{
                            type: 'text',
                            text: JSON.stringify(result, null, 2)
                        }]
                };
            }
            case 'check_phase_transition': {
                const { session_id } = args;
                const result = await checkAndTransitionPhase(session_id);
                return {
                    content: [{
                            type: 'text',
                            text: JSON.stringify(result, null, 2)
                        }]
                };
            }
            case 'delete_claim': {
                const { claim_id } = args;
                const result = await deleteClaim(claim_id);
                return {
                    content: [{
                            type: 'text',
                            text: JSON.stringify(result, null, 2)
                        }]
                };
            }
            case 'delete_multiple_claims': {
                const { claim_ids } = args;
                const result = await deleteMultipleClaims(claim_ids);
                return {
                    content: [{
                            type: 'text',
                            text: JSON.stringify(result, null, 2)
                        }]
                };
            }
            default:
                return {
                    content: [{
                            type: 'text',
                            text: `Unknown tool: ${name}`
                        }],
                    isError: true
                };
        }
    }
    catch (error) {
        return {
            content: [{
                    type: 'text',
                    text: `Error executing ${name}: ${error}`
                }],
            isError: true
        };
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