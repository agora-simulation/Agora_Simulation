import { SimulationProviderConfig } from './provider.model';

export type LlmProvider = 'anthropic' | 'openai' | 'ollama';

export interface Simulation {
  id: string;
  name: string;
  product_description: string;
  target_market: string | null;
  industry: string | null;
  status: SimulationStatus;
  config: SimulationConfig;
  current_tick: number;
  total_ticks: number;
  webhook_url: string | null;
  llm_provider: LlmProvider;
  llm_model_fast: string | null;
  llm_model_smart: string | null;
  provider_config: SimulationProviderConfig | null;
  research_mode: ResearchMode;
  run_group_id: string | null;
  run_index: number | null;
  research_snapshot_id: string | null;
  stagnation_mode: 'off' | 'mild' | 'aggressive';
  distribution_template: Record<string, number> | null;
  created_at: string;
  updated_at: string;
}

export type SimulationStatus = 'pending' | 'researching' | 'research_complete' | 'running' | 'completed' | 'failed';
export type ResearchMode = 'quick' | 'deep';

export interface SimulationConfig {
  persona_count?: number;
  tick_count?: number;
}

export interface SimulationStats {
  simulation_id: string;
  status: SimulationStatus;
  current_tick: number;
  total_ticks: number;
  progress_pct: number;
  persona_count: number;
  post_count: number;
  comment_count: number;
  reaction_count: number;
}

export interface SimulationCreate {
  name: string;
  product_description: string;
  target_market?: string;
  industry?: string;
  config?: SimulationConfig;
  llm_provider?: LlmProvider;
  llm_model_fast?: string | null;
  llm_model_smart?: string | null;
  provider_config?: SimulationProviderConfig | null;
  research_mode?: ResearchMode;
  research_snapshot_id?: string;
  stagnation_mode?: 'off' | 'mild' | 'aggressive';
  distribution_template?: Record<string, number>;
}

export interface SimulationStreamEvent {
  simulation_id: string;
  status: SimulationStatus;
  current_tick: number;
  total_ticks: number;
  progress_pct: number;
}

export interface TickSnapshot {
  id: string;
  simulation_id: string;
  tick_number: number;
  ingame_day: number;
  snapshot: {
    new_posts: number;
    new_comments: number;
    new_reactions: number;
    personas_active: number;
    polarization_index?: number;
    echo_chamber_clusters?: Array<{personas: string[], avg_opinion: number}>;
  };
  created_at: string;
}
