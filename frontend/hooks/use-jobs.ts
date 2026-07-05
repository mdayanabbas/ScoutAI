import { useQuery } from "@tanstack/react-query";

import { listCompanyJobs } from "@/lib/jobs-api";

export const jobKeys = {
  all: ["jobs"] as const,
  company: (companyId: string) => [...jobKeys.all, "company", companyId] as const,
};

export function useCompanyJobs(companyId: string) {
  return useQuery({
    queryKey: jobKeys.company(companyId),
    queryFn: () => listCompanyJobs(companyId, { page: 1, page_size: 20 }),
    enabled: Boolean(companyId),
  });
}
