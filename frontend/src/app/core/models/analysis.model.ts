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
  // v1.1
  sentiment_by_actor_type?: string;
  platform_comparison?: string;
  validator_status?: string;
  trigger_impact?: string;
  stagnation_events?: string;
  function_tag_overview?: string;
  quota_estimates?: Array<Record<string, any>>;
  // Realism Overhaul: ESOMAR
  methodology_section?: string;
  statistical_notes?: string;
  nps_benchmark_comparison?: string;
  created_at: string;
}
