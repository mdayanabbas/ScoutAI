import { api } from "@/lib/api";
import type { MessageResponse, PaginatedResponse } from "@/types/common";
import type {
  Job,
  JobCreateInput,
  JobListItem,
  JobUpdateInput,
  ListCompanyJobsParams,
  ListJobsParams,
} from "@/types/job";

export function listJobs(params: ListJobsParams = {}) {
  return api.get<PaginatedResponse<JobListItem>>("/jobs", params);
}

export function listCompanyJobs(
  companyId: string,
  params: ListCompanyJobsParams = {},
) {
  return api.get<PaginatedResponse<JobListItem>>(
    `/companies/${companyId}/jobs`,
    params,
  );
}

export function getJob(jobId: string) {
  return api.get<Job>(`/jobs/${jobId}`);
}

export function createCompanyJob(companyId: string, data: JobCreateInput) {
  return api.post<Job>(`/companies/${companyId}/jobs`, data);
}

export function updateJob(jobId: string, data: JobUpdateInput) {
  return api.patch<Job>(`/jobs/${jobId}`, data);
}

export function deleteJob(jobId: string) {
  return api.delete<MessageResponse>(`/jobs/${jobId}`);
}
