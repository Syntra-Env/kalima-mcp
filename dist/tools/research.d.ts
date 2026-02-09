import { Claim, Pattern, Evidence } from '../db.js';
export declare function searchClaims(options: {
    phase?: string;
    pattern_id?: string;
    query?: string;
    limit?: number;
}): Promise<Claim[]>;
export declare function getClaimStats(): Promise<{
    total_claims: number;
    by_phase: Record<string, number>;
    total_patterns: number;
    total_evidence: number;
    id_range: {
        min: string;
        max: string;
    };
}>;
export declare function saveBulkInsights(data: {
    claims: Array<{
        content: string;
        phase?: string;
        pattern_id?: string;
    }>;
}): Promise<{
    success: boolean;
    claim_ids: string[];
    message: string;
}>;
export declare function updateClaim(data: {
    claim_id: string;
    content?: string;
    phase?: string;
    pattern_id?: string;
}): Promise<{
    success: boolean;
    message: string;
}>;
export declare function getClaimEvidence(claim_id: string): Promise<Evidence[]>;
export declare function getClaimDependencies(claim_id: string): Promise<{
    claim: Claim | null;
    dependencies: Array<{
        claim: Claim;
        type: string;
    }>;
}>;
export declare function listPatterns(pattern_type?: string): Promise<Pattern[]>;
export declare function saveInsight(data: {
    content: string;
    phase?: string;
    pattern_id?: string;
    evidence_verses?: Array<{
        surah: number;
        ayah: number;
        notes?: string;
    }>;
}): Promise<{
    success: boolean;
    claim_id: string;
    message: string;
}>;
export declare function getClaim(claim_id: string): Promise<Claim | null>;
export declare function deleteClaim(claim_id: string): Promise<{
    success: boolean;
    message: string;
}>;
export declare function deleteMultipleClaims(claim_ids: string[]): Promise<{
    success: boolean;
    deleted: number;
    failed: string[];
    message: string;
}>;
export declare function getVerseClaims(surah: number, ayah: number): Promise<Array<{
    claim_id: string;
    claim_content: string;
    claim_phase: string;
    evidence_type: 'claim_evidence' | 'verse_evidence';
    verification: string | null;
    notes: string | null;
    created_at: string;
}>>;
export declare function findRelatedClaims(claim_id: string, limit?: number): Promise<{
    claim: Claim | null;
    shared_evidence: Array<{
        claim: Claim;
        shared_verses: Array<{
            surah: number;
            ayah: number;
        }>;
    }>;
    same_pattern: Claim[];
    same_surah_claims: Array<{
        claim: Claim;
        surah: number;
    }>;
}>;
export declare function addClaimDependency(data: {
    claim_id: string;
    depends_on_claim_id: string;
    dependency_type: string;
}): Promise<{
    success: boolean;
    message: string;
}>;
export declare function deletePattern(pattern_id: string): Promise<{
    success: boolean;
    message: string;
}>;
//# sourceMappingURL=research.d.ts.map