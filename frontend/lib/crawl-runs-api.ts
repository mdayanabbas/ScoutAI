import { api } from "@/lib/api";
import type { PaginatedResponse } from "@/types/common";
import type {
  CrawlRun,
  CrawlRunMarkFailedInput,
  CrawlRunMarkSuccessInput,
  ListCompanyCrawlRunsParams,
  ListCrawlRunsParams,
} from "@/types/crawl-run";

export function listCompanyCrawlRuns(
  companyId: string,
  params: ListCompanyCrawlRunsParams = {},
) {
  return api.get<PaginatedResponse<CrawlRun>>(
    `/companies/${companyId}/crawl-runs`,
    params,
  );
}

export function listCrawlRuns(params: ListCrawlRunsParams = {}) {
  return api.get<PaginatedResponse<CrawlRun>>("/crawl-runs", params);
}

export function getCrawlRun(crawlRunId: string) {
  return api.get<CrawlRun>(`/crawl-runs/${crawlRunId}`);
}

export function createCompanyCrawlRun(companyId: string) {
  return api.post<CrawlRun>(`/companies/${companyId}/crawl-runs`);
}

export function markCrawlRunRunning(crawlRunId: string) {
  return api.post<CrawlRun>(`/crawl-runs/${crawlRunId}/mark-running`);
}

export function markCrawlRunSuccess(
  crawlRunId: string,
  data: CrawlRunMarkSuccessInput,
) {
  return api.post<CrawlRun>(`/crawl-runs/${crawlRunId}/mark-success`, data);
}

export function markCrawlRunFailed(
  crawlRunId: string,
  data: CrawlRunMarkFailedInput,
) {
  return api.post<CrawlRun>(`/crawl-runs/${crawlRunId}/mark-failed`, data);
}
