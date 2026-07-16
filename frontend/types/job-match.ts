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

export type DiscoverySourceResult = {
  source: "Himalayas" | "We Work Remotely" | "Remotive";
  ok: boolean;
  result?: DiscoveryRunSummary;
  error?: string;
};
