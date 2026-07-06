import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  createCompanyCrawlRun,
  getCrawlRun,
  listCompanyCrawlRuns,
  listCrawlRuns,
  markCrawlRunFailed,
  markCrawlRunRunning,
  markCrawlRunSuccess,
} from "@/lib/crawl-runs-api";
import { dashboardKeys } from "@/hooks/use-dashboard";
import type {
  CrawlRunMarkFailedInput,
  CrawlRunMarkSuccessInput,
  ListCompanyCrawlRunsParams,
  ListCrawlRunsParams,
} from "@/types/crawl-run";

export const crawlRunKeys = {
  all: ["crawl-runs"] as const,
  lists: () => [...crawlRunKeys.all, "list"] as const,
  list: (params: ListCrawlRunsParams) =>
    [...crawlRunKeys.lists(), params] as const,
  companyRoot: ["company-crawl-runs"] as const,
  company: (companyId: string) =>
    [...crawlRunKeys.companyRoot, companyId] as const,
  detail: (crawlRunId: string) =>
    [...crawlRunKeys.all, "detail", crawlRunId] as const,
};

export function useCompanyCrawlRuns(
  companyId: string,
  params: ListCompanyCrawlRunsParams = { page: 1, page_size: 20 },
) {
  return useQuery({
    queryKey: [...crawlRunKeys.company(companyId), params],
    queryFn: () => listCompanyCrawlRuns(companyId, params),
    enabled: Boolean(companyId),
  });
}

export function useCrawlRuns(params: ListCrawlRunsParams = {}) {
  return useQuery({
    queryKey: crawlRunKeys.list(params),
    queryFn: () => listCrawlRuns(params),
  });
}

export function useCrawlRun(crawlRunId: string | null) {
  return useQuery({
    queryKey: crawlRunKeys.detail(crawlRunId ?? ""),
    queryFn: () => getCrawlRun(crawlRunId ?? ""),
    enabled: Boolean(crawlRunId),
  });
}

function invalidateCrawlRunViews(
  queryClient: ReturnType<typeof useQueryClient>,
  companyId: string,
  crawlRunId?: string,
) {
  queryClient.invalidateQueries({ queryKey: crawlRunKeys.company(companyId) });
  queryClient.invalidateQueries({ queryKey: crawlRunKeys.lists() });
  if (crawlRunId) {
    queryClient.invalidateQueries({ queryKey: crawlRunKeys.detail(crawlRunId) });
  }
  queryClient.invalidateQueries({ queryKey: dashboardKeys.all });
}

export function useCreateCompanyCrawlRun(companyId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: () => createCompanyCrawlRun(companyId),
    onSuccess: (run) => {
      invalidateCrawlRunViews(queryClient, companyId, run.id);
    },
  });
}

export function useMarkCrawlRunRunning(companyId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (crawlRunId: string) => markCrawlRunRunning(crawlRunId),
    onSuccess: (run) => {
      invalidateCrawlRunViews(queryClient, companyId, run.id);
    },
  });
}

export function useMarkCrawlRunSuccess(companyId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      crawlRunId,
      data,
    }: {
      crawlRunId: string;
      data: CrawlRunMarkSuccessInput;
    }) => markCrawlRunSuccess(crawlRunId, data),
    onSuccess: (run) => {
      invalidateCrawlRunViews(queryClient, companyId, run.id);
    },
  });
}

export function useMarkCrawlRunFailed(companyId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      crawlRunId,
      data,
    }: {
      crawlRunId: string;
      data: CrawlRunMarkFailedInput;
    }) => markCrawlRunFailed(crawlRunId, data),
    onSuccess: (run) => {
      invalidateCrawlRunViews(queryClient, companyId, run.id);
    },
  });
}
