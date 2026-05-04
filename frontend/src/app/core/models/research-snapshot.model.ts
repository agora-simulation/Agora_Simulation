export interface ResearchPassResult {
  content: string;
  sources: string[];
  confidence: 'HIGH' | 'MEDIUM' | 'LOW';
}

export type ResearchStatus = 'draft' | 'running' | 'completed' | 'approved' | 'archived' | 'failed';

export interface ResearchSnapshot {
  id: string;
  name: string;
  owner_id: string | null;
  provider_id: string | null;
  model: string | null;
  llm_used: string | null;
  prompt: string | null;
  system_prompt: string | null;
  result: string | null;
  template_id: string | null;
  temperature: number | null;
  max_tokens: number;
  passes: Record<string, ResearchPassResult>;
  status: ResearchStatus;
  suggested_triggers: any[];
  error: string | null;
  execution_started_at: string | null;
  execution_finished_at: string | null;
  created_at: string;
  updated_at: string | null;
}

export interface ResearchSnapshotCreate {
  name: string;
  provider_id?: string;
  model?: string;
  prompt?: string;
  system_prompt?: string;
  template_id?: string;
  temperature?: number;
  max_tokens?: number;
}

export interface ResearchExecuteRequest {
  prompt?: string;
  system_prompt?: string;
  provider_id?: string;
  model?: string;
  temperature?: number;
  max_tokens?: number;
}
