import { Claim, Pattern, Evidence } from '../db.js';
export declare function searchClaims(options: {
    phase?: string;
    pattern_id?: string;
    limit?: number;
}): Promise<Claim[]>;
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
export declare function updateClaimPhase(claim_id: string, new_phase: string): Promise<boolean>;
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
//# sourceMappingURL=research.d.ts.map