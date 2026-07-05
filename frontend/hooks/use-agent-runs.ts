import { useQuery } from "@tanstack/react-query";

import { listAgentRuns } from "@/lib/agent-runs-api";

export const agentRunKeys = {
  all: ["agent-runs"] as const,
  company: (companyId: string) =>
    [...agentRunKeys.all, "company", companyId] as const,
};

export function useCompanyAgentRuns(companyId: string) {
  return useQuery({
    queryKey: agentRunKeys.company(companyId),
    queryFn: () =>
      listAgentRuns({ company_id: companyId, page: 1, page_size: 20 }),
    enabled: Boolean(companyId),
  });
}
