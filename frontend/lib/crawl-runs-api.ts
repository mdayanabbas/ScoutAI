import { api } from "@/lib/api";
import type { PaginatedResponse } from "@/types/common";
import type { CrawlRun, ListCompanyCrawlRunsParams } from "@/types/crawl-run";

export function listCompanyCrawlRuns(
  companyId: string,
  params: ListCompanyCrawlRunsParams = {},
) {
  return api.get<PaginatedResponse<CrawlRun>>(
    `/companies/${companyId}/crawl-runs`,
    params,
  );
}
