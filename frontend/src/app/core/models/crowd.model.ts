export interface CrowdState {
  id: string;
  simulation_id: string;
  platform_id: string | null;
  tick: number;
  volume: number;
  sentiment: number;
  polarization: number;
  momentum: number;
  representative_voices: string[];
  created_at: string;
}
