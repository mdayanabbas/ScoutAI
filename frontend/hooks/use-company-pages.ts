import { useQuery } from "@tanstack/react-query";

import { listCompanyPages } from "@/lib/company-pages-api";

export const companyPageKeys = {
  all: ["company-pages"] as const,
  company: (companyId: string) =>
    [...companyPageKeys.all, "company", companyId] as const,
};

export function useCompanyPages(companyId: string) {
  return useQuery({
    queryKey: companyPageKeys.company(companyId),
    queryFn: () => listCompanyPages(companyId, { page: 1, page_size: 20 }),
    enabled: Boolean(companyId),
  });
}
