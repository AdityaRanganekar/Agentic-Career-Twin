export interface User {
  student_id: number;
  name?: string | null;
  username?: string | null;
  email: string;
  auth_provider: string;
}

export interface PlatformLink {
  platform: string;
  url: string;
}

export interface Recommendation {
  skill: string;
  gap_type?: 'Role Gap' | 'Target JD Gap' | 'Role & JD Gap' | string;
  course_title: string;
  url: string;
  platform_links: PlatformLink[];
  justification: string;
  key_topics: string[];
  resource_id?: number | null;
}

export interface ResumeQualityBreakdown {
  quantitative_metrics_score: number;
  production_proof_score: number;
  role_alignment_score: number;
  detected_metrics: string[];
  detected_proof_links: string[];
  detected_production_stack: string[];
}

export interface AnalysisResult {
  student_id: number;
  student_name: string;
  student_email: string;
  readiness_score: number | null;
  score_delta: number | null;
  previous_timestamp: string | null;
  missing_skills: string[] | null;
  jd_fit_score: number | null;
  jd_missing_skills: string[] | null;
  radar_dimensions: Record<string, number> | null;
  jd_radar_dimensions: Record<string, number> | null;
  jd_benchmark_dimensions?: Record<string, number> | null;
  market_corpus_version: string;
  recommendations: Recommendation[];
  student_profile_json: string | null;
  resume_quality_breakdown: ResumeQualityBreakdown | null;
  project_quality_score: number | null;
  jd_quality_breakdown?: ResumeQualityBreakdown | null;
  jd_project_quality_score?: number | null;
  errors: string[];
}

export interface HistoricalRun {
  id: number;
  student_id: number;
  target_role: string;
  readiness_score: number;
  jd_fit_score: number | null;
  project_quality_score: number | null;
  missing_skills: string[];
  jd_missing_skills: string[];
  recommended_resources: Recommendation[];
  resume_filename: string | null;
  timestamp: string;
}

export type ThemeMode = 'light' | 'dark';
export type ActiveTab = 'overview' | 'roadmap' | 'history';

