export interface ResearchPassResult {
  content: string;
  sources: string[];
  confidence: 'HIGH' | 'MEDIUM' | 'LOW';
}

export interface ResearchSnapshot {
  id: string;
  name: string;
  owner_id: string | null;
  llm_used: string | null;
  passes: Record<string, ResearchPassResult>;
  status: 'draft' | 'approved' | 'archived';
  suggested_triggers: any[];
  created_at: string;
  updated_at: string | null;
}

export interface ResearchSnapshotCreate {
  name: string;
  llm_used?: string;
}
