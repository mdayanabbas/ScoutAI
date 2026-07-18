export type CompanyWatchStatus =
  | "watching"
  | "interested"
  | "contacted"
  | "applied"
  | "paused"
  | "archived"
  | string;

export type CompanyWatchPriority = "high" | "medium" | "low" | string;
export type CompanyRemoteInterest =
  | "remote_worldwide"
  | "remote_india"
  | "hybrid_possible"
  | "unknown"
  | string;
export type JuniorFriendlinessSignal = "strong" | "moderate" | "weak" | "unknown" | string;

export type CompanyWatchlistCreate = {
  company_id?: string | null;
  company_name?: string | null;
  company_domain?: string | null;
  company_url?: string | null;
  watch_status?: CompanyWatchStatus;
  priority?: CompanyWatchPriority;
  interest_reason?: string | null;
  target_roles?: string[];
  preferred_locations?: string[];
  notes?: string | null;
  tags?: string[];
  remote_interest?: CompanyRemoteInterest;
  junior_friendliness_signal?: JuniorFriendlinessSignal;
};

export type CompanyWatchlistUpdate = Partial<CompanyWatchlistCreate> & {
  last_reviewed_at?: string | null;
};

export type CompanyWatchlistResponse = {
  id: string;
  company_id?: string | null;
  company_name: string;
  company_domain?: string | null;
  company_url?: string | null;
  watch_status: CompanyWatchStatus;
  priority: CompanyWatchPriority;
  interest_reason?: string | null;
  target_roles?: string[];
  preferred_locations?: string[];
  notes?: string | null;
  tags?: string[];
  remote_interest?: CompanyRemoteInterest;
  junior_friendliness_signal?: JuniorFriendlinessSignal;
  last_reviewed_at?: string | null;
  last_job_seen_at?: string | null;
  job_count?: number;
  recommended_job_count?: number;
  latest_job_title?: string | null;
  latest_job_published_at?: string | null;
  created_at?: string;
  updated_at?: string | null;
};

export type CompanyWatchlistListResponse = {
  items: CompanyWatchlistResponse[];
  total: number;
  limit: number;
  offset: number;
};

export type CompanyWatchlistStatsResponse = {
  total?: number;
  watching?: number;
  interested?: number;
  contacted?: number;
  applied?: number;
  paused?: number;
  archived?: number;
  high_priority?: number;
  medium_priority?: number;
  low_priority?: number;
  with_recommended_jobs?: number;
  with_recent_jobs?: number;
  needs_review?: number;
};

export type CompanyWatchlistJob = {
  id: string;
  company_id?: string | null;
  company_name?: string | null;
  title: string;
  normalized_title?: string | null;
  role_category?: string | null;
  location?: string | null;
  remote_type?: string | null;
  salary_min?: number | string | null;
  salary_max?: number | string | null;
  salary_currency?: string | null;
  job_url?: string | null;
  apply_url?: string | null;
  source_platform?: string | null;
  status?: string | null;
  published_at?: string | null;
  created_at?: string;
  updated_at?: string | null;
  match_tier?: string | null;
  total_score?: number | null;
  eligibility_status?: string | null;
};

export type CompanyWatchlistJobsResponse = {
  watchlist_item: CompanyWatchlistResponse;
  jobs: CompanyWatchlistJob[];
  total: number;
  limit: number;
  offset: number;
};

export type CompanyWatchlistParams = {
  watch_status?: string;
  priority?: string;
  remote_interest?: string;
  junior_friendliness_signal?: string;
  tag?: string;
  search?: string;
  has_recommended_jobs?: boolean;
  has_recent_jobs?: boolean;
  include_archived?: boolean;
  limit?: number;
  offset?: number;
};

export type CompanyWatchlistJobsParams = {
  recommended_only?: boolean;
  active_only?: boolean;
  limit?: number;
  offset?: number;
};
