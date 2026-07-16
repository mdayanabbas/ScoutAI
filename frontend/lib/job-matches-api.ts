import { api } from "@/lib/api";
import type {
  DiscoveryRunSummary,
  RecommendedJobMatchesResponse,
  RecommendedJobMatchParams,
} from "@/types/job-match";

const defaultRecommendationParams = {
  order_by: "recommended",
  limit: 50,
  include_unsuitable: false,
  include_remote_unknown: false,
} as const;

export function fetchRecommendedJobMatches(
  params: RecommendedJobMatchParams = {},
) {
  return api.get<RecommendedJobMatchesResponse>("/job-matches", {
    ...defaultRecommendationParams,
    ...params,
  });
}

export function runHimalayasDiscovery() {
  return api.post<DiscoveryRunSummary>("/discovery/himalayas/jobs", {
    force: true,
    max_queries: 10,
    max_pages_per_query: 2,
    score_after_ingestion: true,
  });
}

export function runWeWorkRemotelyDiscovery() {
  return api.post<DiscoveryRunSummary>("/discovery/we-work-remotely/jobs", {
    force: true,
    include_all_other: true,
    max_items_per_feed: 150,
    score_after_ingestion: true,
  });
}

export function runRemotiveDiscovery() {
  return api.post<DiscoveryRunSummary>("/discovery/remotive/jobs", {
    force: true,
    max_requests: 4,
    limit_per_request: 200,
    score_after_ingestion: true,
  });
}
