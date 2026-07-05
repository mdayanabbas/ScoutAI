import { useQuery } from "@tanstack/react-query";

import { listCompanyCrawlRuns } from "@/lib/crawl-runs-api";

export const crawlRunKeys = {
  all: ["crawl-runs"] as const,
  company: (companyId: string) =>
    [...crawlRunKeys.all, "company", companyId] as const,
};

export function useCompanyCrawlRuns(companyId: string) {
  return useQuery({
    queryKey: crawlRunKeys.company(companyId),
    queryFn: () => listCompanyCrawlRuns(companyId, { page: 1, page_size: 20 }),
    enabled: Boolean(companyId),
  });
}
