import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  createCompanyJob,
  deleteJob,
  getJob,
  listCompanyJobs,
  listJobs,
  updateJob,
} from "@/lib/jobs-api";
import { dashboardKeys } from "@/hooks/use-dashboard";
import type {
  JobCreateInput,
  JobUpdateInput,
  ListCompanyJobsParams,
  ListJobsParams,
} from "@/types/job";

export const jobKeys = {
  all: ["jobs"] as const,
  lists: () => [...jobKeys.all, "list"] as const,
  list: (params: ListJobsParams) => [...jobKeys.lists(), params] as const,
  company: (companyId: string) => [...jobKeys.all, "company", companyId] as const,
  detail: (jobId: string) => [...jobKeys.all, "detail", jobId] as const,
};

export function useJobs(params: ListJobsParams = {}) {
  return useQuery({
    queryKey: jobKeys.list(params),
    queryFn: () => listJobs(params),
  });
}

export function useCompanyJobs(
  companyId: string,
  params: ListCompanyJobsParams = { page: 1, page_size: 20 },
) {
  return useQuery({
    queryKey: [...jobKeys.company(companyId), params],
    queryFn: () => listCompanyJobs(companyId, params),
    enabled: Boolean(companyId),
  });
}

export function useJob(jobId: string | null) {
  return useQuery({
    queryKey: jobKeys.detail(jobId ?? ""),
    queryFn: () => getJob(jobId ?? ""),
    enabled: Boolean(jobId),
  });
}

export function useCreateCompanyJob(companyId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: JobCreateInput) => createCompanyJob(companyId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: jobKeys.company(companyId) });
      queryClient.invalidateQueries({ queryKey: jobKeys.lists() });
      queryClient.invalidateQueries({ queryKey: dashboardKeys.all });
    },
  });
}

export function useUpdateJob() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      jobId,
      companyId,
      data,
    }: {
      jobId: string;
      companyId: string;
      data: JobUpdateInput;
    }) => updateJob(jobId, data),
    onSuccess: (job, variables) => {
      queryClient.invalidateQueries({ queryKey: jobKeys.company(variables.companyId) });
      queryClient.invalidateQueries({ queryKey: jobKeys.detail(job.id) });
      queryClient.invalidateQueries({ queryKey: jobKeys.lists() });
      queryClient.invalidateQueries({ queryKey: dashboardKeys.all });
    },
  });
}

export function useDeleteJob(companyId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (jobId: string) => deleteJob(jobId),
    onSuccess: (_response, jobId) => {
      queryClient.invalidateQueries({ queryKey: jobKeys.company(companyId) });
      queryClient.invalidateQueries({ queryKey: jobKeys.detail(jobId) });
      queryClient.invalidateQueries({ queryKey: jobKeys.lists() });
      queryClient.invalidateQueries({ queryKey: dashboardKeys.all });
    },
  });
}
