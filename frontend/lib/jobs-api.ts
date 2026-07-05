import { api } from "@/lib/api";
import type { PaginatedResponse } from "@/types/common";
import type { Job, ListCompanyJobsParams } from "@/types/job";

export function listCompanyJobs(
  companyId: string,
  params: ListCompanyJobsParams = {},
) {
  return api.get<PaginatedResponse<Job>>(`/companies/${companyId}/jobs`, params);
}
