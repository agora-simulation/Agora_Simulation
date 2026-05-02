export interface AnalysisReport {
  id: string;
  simulation_id: string;
  full_report: string;
  sentiment_over_time: string | null;
  key_turning_points: string | null;
  criticism_points: string | null;
  opportunities: string | null;
  target_segment_analysis: string | null;
  unexpected_findings: string | null;
  influence_network: string | null;
  platform_dynamics: string | null;
  network_evolution: string | null;
  confidence_assessment: string | null;
  methodology_limitations: string | null;
  created_at: string;
}
