export type ProviderType = 'anthropic' | 'openai' | 'ollama';

export interface Provider {
  id: string;
  name: string;
  provider_type: ProviderType;
  base_url: string | null;
  is_default: boolean;
  created_at: string;
  updated_at: string;
}

export interface ProviderCreate {
  name: string;
  provider_type: ProviderType;
  api_key: string;
  base_url?: string | null;
  is_default?: boolean;
}

export interface ProviderUpdate {
  name?: string;
  api_key?: string;
  base_url?: string | null;
  is_default?: boolean;
}

export interface ProviderTestResult {
  success: boolean;
  message: string;
}

export interface PresetPhaseInfo {
  model_tier: string;
  temperature: number;
}

export interface Preset {
  id: string;
  label: string;
  description: string;
  persona_generation: PresetPhaseInfo;
  agent_actions: PresetPhaseInfo;
  state_updates: PresetPhaseInfo;
  analysis_reports: PresetPhaseInfo;
}

export interface PhaseProviderEntry {
  provider_id: string;
  model: string;
  weight: number;
  temperature?: number | null;
  top_p?: number | null;
  top_k?: number | null;
}

export interface PhaseConfig {
  entries: PhaseProviderEntry[];
}

export interface SimulationProviderConfig {
  persona_generation: PhaseConfig;
  agent_actions: PhaseConfig;
  state_updates: PhaseConfig;
  analysis_reports: PhaseConfig;
  preset?: string | null;
}

export interface PhaseBreakdown {
  calls: number;
  estimated_usd: number;
}

export interface CostEstimate {
  total_estimated_usd: number;
  breakdown: Record<string, PhaseBreakdown>;
  per_provider: Record<string, number>;
}

export interface CostEstimateRequest {
  persona_count: number;
  tick_count: number;
  provider_config: SimulationProviderConfig;
}
