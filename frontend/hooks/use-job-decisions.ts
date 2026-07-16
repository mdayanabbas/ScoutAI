import { keepPreviousData, useQuery } from "@tanstack/react-query";

import {
  getJobDecisionStatusCounts,
  listJobDecisions,
} from "@/lib/job-decisions-api";
import type { JobDecisionListParams } from "@/types/job-decision";

export const jobDecisionKeys = {
  all: ["job-decisions"] as const,
  list: (params: JobDecisionListParams = {}) =>
    [...jobDecisionKeys.all, "list", params] as const,
  counts: () => [...jobDecisionKeys.all, "counts"] as const,
};

export function useJobDecisions(params: JobDecisionListParams = {}) {
  return useQuery({
    queryKey: jobDecisionKeys.list(params),
    queryFn: () => listJobDecisions(params),
    placeholderData: keepPreviousData,
  });
}

export function useJobDecisionStatusCounts() {
  return useQuery({
    queryKey: jobDecisionKeys.counts(),
    queryFn: getJobDecisionStatusCounts,
    retry: 1,
  });
}
