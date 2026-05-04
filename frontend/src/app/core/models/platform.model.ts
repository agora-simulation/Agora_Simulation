export interface SimPlatform {
  id: string;
  simulation_id: string | null;
  name: string;
  character: string;
  tonality_modifier: string | null;
  reach_multiplier: number;
  preferred_actor_types: string[];
  echo_chamber_strength: number;
  default_engagement_rate: number;
  is_active: boolean;
  created_at: string;
}

export interface PlatformCreate {
  name: string;
  character: string;
  tonality_modifier?: string;
  reach_multiplier?: number;
  preferred_actor_types?: string[];
  echo_chamber_strength?: number;
  default_engagement_rate?: number;
  simulation_id?: string;
}
