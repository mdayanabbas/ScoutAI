import { useQuery } from "@tanstack/react-query";

import { listCompanyTechStack } from "@/lib/tech-stack-api";

export const techStackKeys = {
  all: ["tech-stack"] as const,
  company: (companyId: string) =>
    [...techStackKeys.all, "company", companyId] as const,
};

export function useCompanyTechStack(companyId: string) {
  return useQuery({
    queryKey: techStackKeys.company(companyId),
    queryFn: () => listCompanyTechStack(companyId),
    enabled: Boolean(companyId),
  });
}
