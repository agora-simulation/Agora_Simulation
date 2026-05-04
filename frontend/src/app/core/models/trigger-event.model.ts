export type TriggerEventType = 'news_headline' | 'competitor_action' | 'regulatory_change' | 'validator_decision' | 'social_incident';
export type TriggerIntensity = 'minor' | 'major' | 'critical';

export interface TriggerEvent {
  id: string;
  simulation_id: string;
  tick_day: number;
  event_type: TriggerEventType;
  title: string;
  content: string | null;
  affected_segments: string[];
  intensity: TriggerIntensity;
  source_attribution: string | null;
  was_auto_generated: boolean;
  created_at: string;
}

export interface TriggerEventCreate {
  simulation_id: string;
  tick_day: number;
  event_type: TriggerEventType;
  title: string;
  content?: string;
  affected_segments?: string[];
  intensity?: TriggerIntensity;
  source_attribution?: string;
}
