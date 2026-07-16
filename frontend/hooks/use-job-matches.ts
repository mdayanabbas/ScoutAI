import { keepPreviousData, useQuery } from "@tanstack/react-query";

import { fetchRecommendedJobMatches } from "@/lib/job-matches-api";
import type { RecommendedJobMatchParams } from "@/types/job-match";

export const jobMatchKeys = {
  all: ["job-matches"] as const,
  recommended: (params: RecommendedJobMatchParams) =>
    [
      ...jobMatchKeys.all,
      "recommended",
      {
        orderBy: params.order_by,
        limit: params.limit,
        offset: params.offset,
        eligibilityStatus: params.eligibility_status,
        matchTier: params.match_tier,
        remoteEligibility: params.remote_eligibility,
        includeUnsuitable: params.include_unsuitable,
        includeRemoteUnknown: params.include_remote_unknown,
        minimumScore: params.minimum_score,
      },
    ] as const,
};

export function useRecommendedJobMatches(params: RecommendedJobMatchParams) {
  return useQuery({
    queryKey: jobMatchKeys.recommended(params),
    queryFn: () => fetchRecommendedJobMatches(params),
    placeholderData: keepPreviousData,
  });
}
