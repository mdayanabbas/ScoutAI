export type MatchTier =
  | "best_match"
  | "strong_match"
  | "worth_checking"
  | "stretch"
  | "unsuitable"
  | string;

export type EligibilityStatus =
  | "eligible"
  | "stretch"
  | "uncertain"
  | "unsuitable"
  | string;

export type RemoteEligibility =
  | "work_from_anywhere"
  | "remote_india_eligible"
  | "remote_global_unspecified"
  | "remote_eligibility_unclear"
  | "unknown"
  | "onsite"
  | "hybrid"
  | "remote_country_restricted"
  | "remote_region_restricted"
  | string;

export type RecommendedJobMatch = {
  job_id: string;
  company_id: string;
  company_name?: string | null;
  title: string;
  role_category?: string | null;
  seniority?: string | null;
  experience_min?: number | null;
  experience_max?: number | null;
  location?: string | null;
  remote_type?: string | null;
  remote_eligibility: RemoteEligibility;
  employment_type?: string | null;
  salary_min?: number | string | null;
  salary_max?: number | string | null;
  salary_currency?: string | null;
  job_url?: string | null;
  apply_url?: string | null;
  published_at?: string | null;
  enrichment_status: string;
  eligibility_status: EligibilityStatus;
  eligibility_reason?: string | null;
  match_tier: MatchTier;
  total_score: number;
  role_score?: number | null;
  remote_score?: number | null;
  seniority_score?: number | null;
  experience_score?: number | null;
  positive_signals?: string[];
  negative_signals?: string[];
  missing_information?: string[];
  scored_at: string;
  is_stale?: boolean;
  actionability_status?: string | null;
  valid_job_url?: boolean | null;
  valid_apply_url?: boolean | null;
};

export type RecommendedJobMatchesResponse = {
  items: RecommendedJobMatch[];
  total: number;
  limit: number;
  offset: number;
};

export type RecommendedJobMatchParams = {
  order_by?: "recommended" | "score" | "newest" | "salary";
  limit?: number;
  offset?: number;
  eligibility_status?: string;
  match_tier?: string;
  remote_eligibility?: string;
  include_unsuitable?: boolean;
  include_remote_unknown?: boolean;
  minimum_score?: number;
};

export type DiscoveryRunSummary = {
  discovery_run_id?: string | null;
  status?: string;
  reason?: string | null;
  jobs_created?: number;
  jobs_existing?: number;
  jobs_updated?: number;
  jobs_scored?: number;
  candidates_rejected?: number;
};

export type RemoteDiscoverySourceResult = {
  source: "himalayas" | "we_work_remotely" | "remotive" | string;
  status?: string;
  reason?: string | null;
  discovery_run_id?: string | null;
  started_at?: string;
  finished_at?: string;
  duration_ms?: number;
  jobs_created?: number;
  jobs_existing?: number;
  jobs_updated?: number;
  jobs_scored?: number;
  jobs_failed?: number;
  candidates_created?: number;
  candidates_existing?: number;
  candidates_rejected?: number;
  provider_records_seen?: number;
  unique_records?: number;
  accepted_jobs_count?: number;
  rejected_samples_count?: number;
  accepted_jobs?: Array<Record<string, unknown>>;
  rejected_samples?: Array<Record<string, unknown>>;
  warnings?: string[];
  error?: string | null;
};

export type RemoteDiscoveryRecommendationSummary = {
  job_id: string;
  company_name?: string | null;
  title: string;
  remote_eligibility: string;
  match_tier: string;
  eligibility_status: string;
  total_score: number;
  salary_min?: number | string | null;
  salary_max?: number | string | null;
  salary_currency?: string | null;
  job_url?: string | null;
  apply_url?: string | null;
  eligibility_reason?: string | null;
};

export type RemoteJobDiscoveryOrchestratorResult = {
  status: "succeeded" | "partial" | "failed" | "skipped" | string;
  reason?: string | null;
  profile_id?: string | null;
  sources_planned?: string[];
  sources_completed?: number;
  sources_failed?: number;
  sources_skipped?: number;
  total_provider_records_seen?: number;
  total_unique_records?: number;
  total_candidates_created?: number;
  total_candidates_existing?: number;
  total_candidates_rejected?: number;
  total_jobs_created?: number;
  total_jobs_existing?: number;
  total_jobs_updated?: number;
  total_jobs_scored?: number;
  total_jobs_failed?: number;
  source_results?: RemoteDiscoverySourceResult[];
  top_recommendations?: RemoteDiscoveryRecommendationSummary[];
  started_at?: string;
  finished_at?: string;
  duration_ms?: number;
  warnings?: string[];
};
