import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  createAgentRun,
  createAgentRunStep,
  deleteAgentStep,
  getAgentRun,
  listAgentRuns,
  listAgentRunSteps,
  markAgentRunFailed,
  markAgentRunRunning,
  markAgentRunSuccess,
  updateAgentStep,
} from "@/lib/agent-runs-api";
import { dashboardKeys } from "@/hooks/use-dashboard";
import type {
  AgentRunCreateInput,
  AgentRunMarkFailedInput,
  AgentRunMarkSuccessInput,
  AgentStepCreateInput,
  AgentStepUpdateInput,
  ListAgentRunsParams,
} from "@/types/agent-run";

export const agentRunKeys = {
  all: ["agent-runs"] as const,
  list: (params: ListAgentRunsParams) => [...agentRunKeys.all, params] as const,
  companyRoot: ["company-agent-runs"] as const,
  company: (companyId: string) =>
    [...agentRunKeys.companyRoot, companyId] as const,
  detailRoot: ["agent-run"] as const,
  detail: (agentRunId: string) =>
    [...agentRunKeys.detailRoot, agentRunId] as const,
  stepsRoot: ["agent-run-steps"] as const,
  steps: (agentRunId: string) =>
    [...agentRunKeys.stepsRoot, agentRunId] as const,
};

export function useAgentRuns(params: ListAgentRunsParams = {}) {
  return useQuery({
    queryKey: agentRunKeys.list(params),
    queryFn: () => listAgentRuns(params),
  });
}

export function useCompanyAgentRuns(companyId: string) {
  return useQuery({
    queryKey: agentRunKeys.company(companyId),
    queryFn: () =>
      listAgentRuns({ company_id: companyId, page: 1, page_size: 20 }),
    enabled: Boolean(companyId),
  });
}

export function useAgentRun(agentRunId: string | null) {
  return useQuery({
    queryKey: agentRunKeys.detail(agentRunId ?? ""),
    queryFn: () => getAgentRun(agentRunId ?? ""),
    enabled: Boolean(agentRunId),
  });
}

export function useAgentRunSteps(agentRunId: string | null) {
  return useQuery({
    queryKey: agentRunKeys.steps(agentRunId ?? ""),
    queryFn: () => listAgentRunSteps(agentRunId ?? ""),
    enabled: Boolean(agentRunId),
  });
}

function invalidateAgentRunViews(
  queryClient: ReturnType<typeof useQueryClient>,
  companyId: string,
  agentRunId?: string,
) {
  queryClient.invalidateQueries({ queryKey: agentRunKeys.company(companyId) });
  queryClient.invalidateQueries({ queryKey: agentRunKeys.all });
  if (agentRunId) {
    queryClient.invalidateQueries({ queryKey: agentRunKeys.detail(agentRunId) });
    queryClient.invalidateQueries({ queryKey: agentRunKeys.steps(agentRunId) });
  }
  queryClient.invalidateQueries({ queryKey: dashboardKeys.all });
}

export function useCreateAgentRun(companyId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: AgentRunCreateInput) =>
      createAgentRun({ ...data, company_id: companyId }),
    onSuccess: (run) => {
      invalidateAgentRunViews(queryClient, companyId, run.id);
    },
  });
}

export function useMarkAgentRunRunning(companyId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (agentRunId: string) => markAgentRunRunning(agentRunId),
    onSuccess: (run) => {
      invalidateAgentRunViews(queryClient, companyId, run.id);
    },
  });
}

export function useMarkAgentRunSuccess(companyId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      agentRunId,
      data,
    }: {
      agentRunId: string;
      data: AgentRunMarkSuccessInput;
    }) => markAgentRunSuccess(agentRunId, data),
    onSuccess: (run) => {
      invalidateAgentRunViews(queryClient, companyId, run.id);
    },
  });
}

export function useMarkAgentRunFailed(companyId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      agentRunId,
      data,
    }: {
      agentRunId: string;
      data: AgentRunMarkFailedInput;
    }) => markAgentRunFailed(agentRunId, data),
    onSuccess: (run) => {
      invalidateAgentRunViews(queryClient, companyId, run.id);
    },
  });
}

export function useCreateAgentRunStep(agentRunId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: AgentStepCreateInput) =>
      createAgentRunStep(agentRunId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: agentRunKeys.steps(agentRunId) });
      queryClient.invalidateQueries({ queryKey: agentRunKeys.detail(agentRunId) });
    },
  });
}

export function useUpdateAgentStep(agentRunId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      stepId,
      data,
    }: {
      stepId: string;
      data: AgentStepUpdateInput;
    }) => updateAgentStep(stepId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: agentRunKeys.steps(agentRunId) });
      queryClient.invalidateQueries({ queryKey: agentRunKeys.detail(agentRunId) });
    },
  });
}

export function useDeleteAgentStep(agentRunId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (stepId: string) => deleteAgentStep(stepId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: agentRunKeys.steps(agentRunId) });
      queryClient.invalidateQueries({ queryKey: agentRunKeys.detail(agentRunId) });
    },
  });
}
