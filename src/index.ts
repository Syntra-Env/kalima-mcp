#!/usr/bin/env node

import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
  Tool,
} from '@modelcontextprotocol/sdk/types.js';

import { getVerse, getSurah, listSurahs, searchVerses } from './tools/quran.js';
import {
  searchClaims,
  getClaimEvidence,
  getClaimDependencies,
  listPatterns,
  saveInsight,
  getClaim,
  deleteClaim,
  deleteMultipleClaims,
  getVerseClaims,
  getClaimStats,
  saveBulkInsights,
  updateClaim,
  findRelatedClaims,
  addClaimDependency,
  deletePattern
} from './tools/research.js';
import {
  searchByLinguisticFeatures,
  createPatternInterpretation,
  createSurahTheme,
  addVerseEvidence
} from './tools/linguistic.js';
import {
  startWorkflowSession,
  getNextVerseInWorkflow,
  submitVerification,
  getWorkflowStats,
  listWorkflowSessions,
  checkAndTransitionPhase
} from './tools/workflow.js';
import { getVerseWithContext } from './tools/context.js';
import { closeDatabase } from './db.js';
import { jsonResponse, errorResponse } from './utils/dbHelpers.js';

// Tool handler type
type ToolHandler = (args: Record<string, any>) => Promise<unknown>;

// Tool handlers - each returns data, serialization is handled by the dispatch wrapper
const handlers: Record<string, ToolHandler> = {
  get_verse: async (args) => {
    const verse = await getVerse(args.surah, args.ayah);
    if (!verse) return { error: `Verse ${args.surah}:${args.ayah} not found` };
    return verse;
  },

  get_surah: async (args) => {
    const result = await getSurah(args.surah);
    if (!result) return { error: `Surah ${args.surah} not found` };
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
    if (!claim) return { error: `Claim ${args.claim_id} not found` };
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
    return await saveInsight(args as any);
  },

  search_by_linguistic_features: async (args) => {
    return await searchByLinguisticFeatures(args as any);
  },

  create_pattern_interpretation: async (args) => {
    return await createPatternInterpretation(args as any);
  },

  create_surah_theme: async (args) => {
    return await createSurahTheme(args as any);
  },

  add_verse_evidence: async (args) => {
    return await addVerseEvidence(args as any);
  },

  start_workflow_session: async (args) => {
    return await startWorkflowSession(args as any);
  },

  get_next_verse: async (args) => {
    return await getNextVerseInWorkflow(args.session_id);
  },

  submit_verification: async (args) => {
    return await submitVerification(args as any);
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
    return await saveBulkInsights(args as any);
  },

  update_claim: async (args) => {
    return await updateClaim(args as any);
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
    return await addClaimDependency(args as any);
  },

  delete_pattern: async (args) => {
    return await deletePattern(args.pattern_id);
  }
};

// Tool definitions
const tools: Tool[] = [
  {
    name: 'get_verse',
    description: 'Retrieve a specific verse from the Quran with ONLY its Arabic text. DO NOT add English translations when presenting verses to the user. Only show interpretations if they exist in the database. Use this when the user asks about a specific verse (e.g., "Show me verse 2:255").',
    inputSchema: {
      type: 'object',
      properties: {
        surah: { type: 'number', description: 'The surah (chapter) number (1-114)', minimum: 1, maximum: 114 },
        ayah: { type: 'number', description: 'The ayah (verse) number within the surah', minimum: 1 }
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
        surah: { type: 'number', description: 'The surah (chapter) number (1-114)', minimum: 1, maximum: 114 }
      },
      required: ['surah']
    }
  },
  {
    name: 'list_surahs',
    description: 'Get a list of all 114 surahs with their Arabic names and verse counts. Use this when the user wants to browse chapters or know chapter names.',
    inputSchema: { type: 'object', properties: {}, required: [] }
  },
  {
    name: 'search_verses',
    description: 'Search for verses containing specific Arabic text. Use this for finding verses with particular words or phrases.',
    inputSchema: {
      type: 'object',
      properties: {
        query: { type: 'string', description: 'Arabic text to search for' },
        limit: { type: 'number', description: 'Maximum number of results (default: 20)', minimum: 1, maximum: 100 }
      },
      required: ['query']
    }
  },
  {
    name: 'search_claims',
    description: 'Search research claims by keyword, phase, or pattern. Returns claims matching the specified filters. Use this for broad searches (e.g., "find all claims about roots"). For a specific claim by ID, use get_claim instead. For claims linked to a specific verse, use get_verse_claims.',
    inputSchema: {
      type: 'object',
      properties: {
        query: { type: 'string', description: 'Search keyword(s) to match against claim content (case-insensitive substring match)' },
        phase: { type: 'string', description: 'Filter by research phase', enum: ['question', 'hypothesis', 'validation', 'active_verification', 'passive_verification'] },
        pattern_id: { type: 'string', description: 'Filter by pattern ID if looking for claims related to a specific pattern' },
        limit: { type: 'number', description: 'Maximum number of results (default: 50)', minimum: 1, maximum: 200 }
      },
      required: []
    }
  },
  {
    name: 'get_claim',
    description: 'Get a single claim by its ID. Returns the full claim including content, phase, pattern_id, and timestamps. Use this when you know the exact claim ID. For keyword search use search_claims; for verse-linked claims use get_verse_claims.',
    inputSchema: {
      type: 'object',
      properties: {
        claim_id: { type: 'string', description: 'The claim ID (e.g., "claim_42")' }
      },
      required: ['claim_id']
    }
  },
  {
    name: 'get_claim_evidence',
    description: 'Get all evidence (verse references) supporting a specific research claim.',
    inputSchema: {
      type: 'object',
      properties: {
        claim_id: { type: 'string', description: 'The unique identifier of the claim' }
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
        claim_id: { type: 'string', description: 'The unique identifier of the claim' }
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
        pattern_type: { type: 'string', description: 'Filter by pattern type', enum: ['morphological', 'syntactic', 'semantic'] }
      },
      required: []
    }
  },
  {
    name: 'save_insight',
    description: 'Save a single research claim or insight discovered during conversation. Use this to preserve important observations for future research. When saving 2+ claims at once, prefer save_bulk_insights instead -- it is significantly faster.',
    inputSchema: {
      type: 'object',
      properties: {
        content: { type: 'string', description: 'The claim or insight text' },
        phase: { type: 'string', description: 'Current research phase (default: question)', enum: ['question', 'hypothesis', 'validation'], default: 'question' },
        pattern_id: { type: 'string', description: 'Optional pattern ID this claim relates to' },
        evidence_verses: {
          type: 'array',
          description: 'Array of verse references as evidence',
          items: {
            type: 'object',
            properties: { surah: { type: 'number' }, ayah: { type: 'number' }, notes: { type: 'string' } },
            required: ['surah', 'ayah']
          }
        }
      },
      required: ['content']
    }
  },
  {
    name: 'search_by_linguistic_features',
    description: 'Search verses by linguistic features like part of speech, verb form, mood, aspect, root, etc. Use this for linguistic analysis like finding all present tense verbs, imperatives, or words from a specific root.',
    inputSchema: {
      type: 'object',
      properties: {
        pos: { type: 'string', description: 'Part of speech (e.g., "VERB", "NOUN", "ADJ", "PRON")' },
        aspect: { type: 'string', description: 'Verb aspect: "imperfective" (present tense) or "perfective" (past tense)' },
        mood: { type: 'string', description: 'Verb mood: "indicative", "subjunctive", "imperative", "jussive"' },
        verb_form: { type: 'string', description: 'Specific verb form' },
        voice: { type: 'string', description: 'Voice: "active" or "passive"' },
        person: { type: 'string', description: 'Grammatical person: "1st", "2nd", "3rd"' },
        number: { type: 'string', description: 'Number: "singular", "dual", "plural"' },
        gender: { type: 'string', description: 'Gender: "masculine", "feminine"' },
        root: { type: 'string', description: 'Arabic root (e.g., "ق-و-ل" for speech/saying)' },
        lemma: { type: 'string', description: 'Base word form' },
        case_value: { type: 'string', description: 'Grammatical case: "nominative", "accusative", "genitive"' },
        dependency_rel: { type: 'string', description: 'Syntactic dependency relation' },
        role: { type: 'string', description: 'Grammatical role in sentence' },
        surah: { type: 'number', description: 'Limit search to specific surah', minimum: 1, maximum: 114 },
        limit: { type: 'number', description: 'Maximum number of results (default: 50)', minimum: 1, maximum: 200, default: 50 }
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
        description: { type: 'string', description: 'Description of the pattern (e.g., "Present tense verbs in the Quran")' },
        pattern_type: { type: 'string', description: 'Type of pattern', enum: ['morphological', 'syntactic', 'semantic'] },
        interpretation: { type: 'string', description: 'The interpretation or meaning of this pattern' },
        linguistic_features: { type: 'object', description: 'The linguistic features that define this pattern (e.g., {pos: "VERB", aspect: "imperfective"})' },
        scope: { type: 'string', description: 'Scope of the pattern (default: "all_verses")', default: 'all_verses' },
        phase: { type: 'string', description: 'Research phase (default: "hypothesis")', enum: ['question', 'hypothesis', 'validation', 'verification'], default: 'hypothesis' }
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
        surah: { type: 'number', description: 'The surah number (1-114)', minimum: 1, maximum: 114 },
        theme: { type: 'string', description: 'The main theme of the surah' },
        description: { type: 'string', description: 'Additional description or details about the theme' },
        phase: { type: 'string', description: 'Research phase (default: "hypothesis")', enum: ['question', 'hypothesis', 'validation', 'verification'], default: 'hypothesis' }
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
        claim_id: { type: 'string', description: 'The claim or pattern ID this evidence relates to' },
        surah: { type: 'number', description: 'The surah number', minimum: 1, maximum: 114 },
        ayah: { type: 'number', description: 'The ayah number', minimum: 1 },
        verification: { type: 'string', description: 'Verification result', enum: ['supports', 'contradicts', 'unclear'] },
        notes: { type: 'string', description: 'Optional notes about this verification' }
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
        claim_id: { type: 'string', description: 'The claim or pattern ID to verify' },
        workflow_type: { type: 'string', description: 'Type of workflow', enum: ['pattern', 'surah_theme'] },
        linguistic_features: { type: 'object', description: 'For pattern workflow: the linguistic features to search (e.g., {pos: "VERB", aspect: "imperfective"})' },
        surah: { type: 'number', description: 'For surah_theme workflow: the surah number to verify', minimum: 1, maximum: 114 },
        limit: { type: 'number', description: 'For pattern workflow: maximum number of verses (default: 100)', minimum: 1, maximum: 500, default: 100 }
      },
      required: ['claim_id', 'workflow_type']
    }
  },
  {
    name: 'get_next_verse',
    description: 'Get the next verse in an active workflow session for verification. Returns ONLY the Arabic verse text, progress, and completion status. DO NOT add English translations when presenting verses to the user.',
    inputSchema: {
      type: 'object',
      properties: {
        session_id: { type: 'string', description: 'The workflow session ID' }
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
        session_id: { type: 'string', description: 'The workflow session ID' },
        verification: { type: 'string', description: 'Verification result for current verse', enum: ['supports', 'contradicts', 'unclear'] },
        notes: { type: 'string', description: 'Optional notes about this verification' }
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
        session_id: { type: 'string', description: 'The workflow session ID' }
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
        status: { type: 'string', description: 'Optional status filter', enum: ['active', 'completed', 'paused'] }
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
        session_id: { type: 'string', description: 'The workflow session ID' }
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
        claim_id: { type: 'string', description: 'The claim ID to delete (format: claim_123)' }
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
        claim_ids: { type: 'array', description: 'Array of claim IDs to delete', items: { type: 'string' } }
      },
      required: ['claim_ids']
    }
  },
  {
    name: 'get_claim_stats',
    description: 'Get database statistics: total claims, breakdown by phase, total patterns, total evidence links, and claim ID range. Use this for a quick overview of the database state.',
    inputSchema: { type: 'object', properties: {}, required: [] }
  },
  {
    name: 'save_bulk_insights',
    description: 'Save multiple research claims at once in a single operation. Much more efficient than calling save_insight repeatedly. Each claim gets its own sequential ID. Does not support evidence_verses -- use add_verse_evidence separately after saving if needed.',
    inputSchema: {
      type: 'object',
      properties: {
        claims: {
          type: 'array',
          description: 'Array of claims to save',
          items: {
            type: 'object',
            properties: {
              content: { type: 'string', description: 'The claim or insight text' },
              phase: { type: 'string', description: 'Research phase (default: question)', enum: ['question', 'hypothesis', 'validation'] },
              pattern_id: { type: 'string', description: 'Optional pattern ID this claim relates to' }
            },
            required: ['content']
          }
        }
      },
      required: ['claims']
    }
  },
  {
    name: 'update_claim',
    description: 'Update an existing claim\'s content, phase, or pattern_id. Use this to edit claim text, change research phase (question/hypothesis/validation/active_verification/passive_verification), or link to a pattern. This is the only tool for modifying existing claims.',
    inputSchema: {
      type: 'object',
      properties: {
        claim_id: { type: 'string', description: 'The claim ID to update' },
        content: { type: 'string', description: 'New content text for the claim' },
        phase: { type: 'string', description: 'New research phase', enum: ['question', 'hypothesis', 'validation', 'active_verification', 'passive_verification'] },
        pattern_id: { type: 'string', description: 'Pattern ID to link this claim to' }
      },
      required: ['claim_id']
    }
  },
  {
    name: 'get_verse_claims',
    description: 'Get all claims that reference a specific verse as evidence. Use this to check existing interpretations before adding new claims about a verse, and to detect potential contradictions. For morphology-aware analysis with word-level claims, use get_verse_with_context instead.',
    inputSchema: {
      type: 'object',
      properties: {
        surah: { type: 'number', description: 'The surah (chapter) number (1-114)', minimum: 1, maximum: 114 },
        ayah: { type: 'number', description: 'The ayah (verse) number', minimum: 1 }
      },
      required: ['surah', 'ayah']
    }
  },
  {
    name: 'get_verse_with_context',
    description: 'Get a verse with morphology-aware claim context. For each word, surfaces related claims based on its root, verb form, and POS from the pattern_linguistic_features table. More comprehensive than get_verse_claims but heavier. Use when you need to understand what is already known about each word in the verse.',
    inputSchema: {
      type: 'object',
      properties: {
        surah: { type: 'number', description: 'The surah (chapter) number (1-114)', minimum: 1, maximum: 114 },
        ayah: { type: 'number', description: 'The ayah (verse) number', minimum: 1 },
        include_root_claims: { type: 'boolean', description: 'Include claims about word roots (default: true)', default: true },
        include_form_claims: { type: 'boolean', description: 'Include claims about verb forms (default: true)', default: true },
        include_pos_claims: { type: 'boolean', description: 'Include claims about parts of speech (default: true)', default: true }
      },
      required: ['surah', 'ayah']
    }
  },
  {
    name: 'find_related_claims',
    description: 'Find claims structurally related to a given claim through shared verse evidence, shared patterns, or same-surah evidence. Use this to discover non-obvious connections between claims. Returns claims grouped by relationship type.',
    inputSchema: {
      type: 'object',
      properties: {
        claim_id: { type: 'string', description: 'The claim ID to find related claims for' },
        limit: { type: 'number', description: 'Maximum results per relationship type (default: 20)', minimum: 1, maximum: 100, default: 20 }
      },
      required: ['claim_id']
    }
  },
  {
    name: 'add_claim_dependency',
    description: 'Create a typed relationship between two claims. Use this to record that one claim depends on, supports, contradicts, or refines another. These relationships are surfaced by get_claim_dependencies.',
    inputSchema: {
      type: 'object',
      properties: {
        claim_id: { type: 'string', description: 'The source claim ID' },
        depends_on_claim_id: { type: 'string', description: 'The target claim ID' },
        dependency_type: { type: 'string', description: 'Type of relationship', enum: ['depends_on', 'supports', 'contradicts', 'refines', 'related'] }
      },
      required: ['claim_id', 'depends_on_claim_id', 'dependency_type']
    }
  },
  {
    name: 'delete_pattern',
    description: 'Delete a pattern and unlink any claims that reference it (claims are preserved, their pattern_id is set to null). Use this to clean up duplicate or test patterns.',
    inputSchema: {
      type: 'object',
      properties: {
        pattern_id: { type: 'string', description: 'The pattern ID to delete (e.g., "pattern_24")' }
      },
      required: ['pattern_id']
    }
  }
];

// Create MCP server
const server = new Server(
  { name: 'kalima-mcp-server', version: '1.0.0' },
  { capabilities: { tools: {} } }
);

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
  } catch (error) {
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
