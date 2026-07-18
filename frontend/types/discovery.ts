export type DiscoverySource =
  | "himalayas"
  | "we_work_remotely"
  | "remotive"
  | "hacker_news"
  | "ycombinator"
  | "ashby"
  | string;

export type HimalayasRemoteDiscoveryOptions = {
  max_queries?: number | null;
  max_pages_per_query?: number | null;
};

export type WWRRemoteDiscoveryOptions = {
  include_all_other?: boolean | null;
  max_items_per_feed?: number | null;
};

export type RemotiveRemoteDiscoveryOptions = {
  max_requests?: number | null;
  limit_per_request?: number | null;
};

export type HackerNewsRemoteDiscoveryOptions = {
  enabled?: boolean | null;
  feeds?: string[] | null;
  limit?: number | null;
  lookback_days?: number | null;
  minimum_score?: number | null;
  include_items_without_website?: boolean | null;
  enrich_domains?: boolean | null;
  ingest_jobs?: boolean | null;
  enrich_jobs?: boolean | null;
  score_jobs?: boolean | null;
};

export type YCombinatorRemoteDiscoveryOptions = {
  enabled?: boolean | null;
  max_pages?: number | null;
  remote_only?: boolean | null;
  include_recent_only?: boolean | null;
  lookback_days?: number | null;
  ingest_jobs?: boolean | null;
  enrich_jobs?: boolean | null;
  score_jobs?: boolean | null;
};

export type AshbyRemoteDiscoveryOptions = {
  enabled?: boolean | null;
  board_slugs?: string[] | null;
  max_jobs_per_board?: number | null;
  enrich_jobs?: boolean | null;
  score_jobs?: boolean | null;
};

export type RemoteJobDiscoveryRunRequest = {
  force?: boolean;
  sources?: DiscoverySource[] | null;
  score_after_ingestion?: boolean | null;
  himalayas?: HimalayasRemoteDiscoveryOptions | null;
  we_work_remotely?: WWRRemoteDiscoveryOptions | null;
  remotive?: RemotiveRemoteDiscoveryOptions | null;
  hacker_news?: HackerNewsRemoteDiscoveryOptions | null;
  ycombinator?: YCombinatorRemoteDiscoveryOptions | null;
  ashby?: AshbyRemoteDiscoveryOptions | null;
};

export type RemoteDiscoveryTopRecommendation = {
  job_id?: string | null;
  company_name?: string | null;
  title?: string | null;
  remote_eligibility?: string | null;
  match_tier?: string | null;
  eligibility_status?: string | null;
  total_score?: number | string | null;
  salary_min?: number | string | null;
  salary_max?: number | string | null;
  salary_currency?: string | null;
  job_url?: string | null;
  apply_url?: string | null;
  eligibility_reason?: string | null;
};

export type RemoteDiscoverySourceResult = {
  source?: DiscoverySource | null;
  status?: string | null;
  reason?: string | null;
  discovery_run_id?: string | null;
  started_at?: string | null;
  finished_at?: string | null;
  duration_ms?: number | null;
  provider_records_seen?: number | null;
  unique_records?: number | null;
  candidates_created?: number | null;
  candidates_existing?: number | null;
  candidates_rejected?: number | null;
  candidates_found?: number | null;
  candidates_normalized?: number | null;
  candidates_deferred?: number | null;
  candidates_failed?: number | null;
  companies_created?: number | null;
  companies_matched?: number | null;
  domains_resolved?: number | null;
  domains_unresolved?: number | null;
  jobs_created?: number | null;
  jobs_existing?: number | null;
  jobs_updated?: number | null;
  jobs_skipped?: number | null;
  jobs_enriched?: number | null;
  jobs_scored?: number | null;
  jobs_failed?: number | null;
  accepted_jobs_count?: number | null;
  rejected_samples_count?: number | null;
  accepted_jobs?: Array<Record<string, unknown>> | null;
  rejected_samples?: Array<Record<string, unknown>> | null;
  warnings?: string[] | null;
  error?: string | null;
  diagnostics?: Record<string, unknown> | null;
};

export type RemoteJobDiscoveryOrchestratorResult = {
  status?: "succeeded" | "partial" | "failed" | "skipped" | string | null;
  reason?: string | null;
  profile_id?: string | null;
  sources_planned?: DiscoverySource[] | null;
  sources_completed?: number | null;
  sources_failed?: number | null;
  sources_skipped?: number | null;
  total_provider_records_seen?: number | null;
  total_unique_records?: number | null;
  total_candidates_created?: number | null;
  total_candidates_existing?: number | null;
  total_candidates_rejected?: number | null;
  total_jobs_created?: number | null;
  total_jobs_existing?: number | null;
  total_jobs_updated?: number | null;
  total_jobs_scored?: number | null;
  total_jobs_failed?: number | null;
  source_results?: RemoteDiscoverySourceResult[] | null;
  top_recommendations?: RemoteDiscoveryTopRecommendation[] | null;
  started_at?: string | null;
  finished_at?: string | null;
  duration_ms?: number | null;
  warnings?: string[] | null;
  recommendation_scope?: string | null;
  recommendation_source_filter?: string[] | null;
  recommendation_job_ids_count?: number | null;
};

export type RemoteJobDiscoveryPlan = {
  profile_id?: string | null;
  enabled_sources?: DiscoverySource[] | null;
  disabled_sources?: DiscoverySource[] | null;
  cooldowns?: Record<string, Record<string, unknown>> | null;
  himalayas?: Record<string, unknown> | null;
  we_work_remotely?: Record<string, unknown> | null;
  remotive?: Record<string, unknown> | null;
  hacker_news?: Record<string, unknown> | null;
  ycombinator?: Record<string, unknown> | null;
  ashby?: Record<string, unknown> | null;
  available_sources?: Array<{
    source?: DiscoverySource | null;
    enabled_by_default?: boolean | null;
    description?: string | null;
    expected_behavior?: string | null;
    required_options?: string[] | null;
  }> | null;
  recommended_defaults?: Record<string, unknown> | null;
  warnings?: string[] | null;
};

export type DiscoveryRunListItem = {
  id?: string | null;
  source?: string | null;
  status?: string | null;
  started_at?: string | null;
  finished_at?: string | null;
  duration_ms?: number | null;
  provider_records_seen?: number | null;
  candidates_found?: number | null;
  candidates_normalized?: number | null;
  candidates_deferred?: number | null;
  candidates_created?: number | null;
  candidates_rejected?: number | null;
  candidates_failed?: number | null;
  companies_created?: number | null;
  companies_matched?: number | null;
  domains_resolved?: number | null;
  domains_unresolved?: number | null;
  jobs_created?: number | null;
  jobs_existing?: number | null;
  jobs_enriched?: number | null;
  jobs_scored?: number | null;
  jobs_failed?: number | null;
  warnings?: string[] | null;
  error_message?: string | null;
  metadata?: Record<string, unknown> | null;
  metadata_json?: Record<string, unknown> | null;
  [key: string]: unknown;
};

export type DiscoveryRunsResponse = {
  items?: DiscoveryRunListItem[] | null;
  total?: number | null;
  limit?: number | null;
  offset?: number | null;
};
