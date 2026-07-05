import { api } from "@/lib/api";
import type {
  AgentRun,
  AgentRunCreateInput,
  AgentRunMarkFailedInput,
  AgentRunMarkSuccessInput,
  AgentStep,
  AgentStepCreateInput,
  AgentStepUpdateInput,
  ListAgentRunsParams,
} from "@/types/agent-run";
import type { MessageResponse, PaginatedResponse } from "@/types/common";

export function listAgentRuns(params: ListAgentRunsParams = {}) {
  return api.get<PaginatedResponse<AgentRun>>("/agent-runs", params);
}

export function getAgentRun(agentRunId: string) {
  return api.get<AgentRun>(`/agent-runs/${agentRunId}`);
}

export function createAgentRun(data: AgentRunCreateInput) {
  return api.post<AgentRun>("/agent-runs", data);
}

export function markAgentRunRunning(agentRunId: string) {
  return api.post<AgentRun>(`/agent-runs/${agentRunId}/mark-running`);
}

export function markAgentRunSuccess(
  agentRunId: string,
  data: AgentRunMarkSuccessInput,
) {
  return api.post<AgentRun>(`/agent-runs/${agentRunId}/mark-success`, data);
}

export function markAgentRunFailed(
  agentRunId: string,
  data: AgentRunMarkFailedInput,
) {
  return api.post<AgentRun>(`/agent-runs/${agentRunId}/mark-failed`, data);
}

export function listAgentRunSteps(agentRunId: string) {
  return api.get<AgentStep[]>(`/agent-runs/${agentRunId}/steps`);
}

export function createAgentRunStep(
  agentRunId: string,
  data: AgentStepCreateInput,
) {
  return api.post<AgentStep>(`/agent-runs/${agentRunId}/steps`, data);
}

export function updateAgentStep(stepId: string, data: AgentStepUpdateInput) {
  return api.patch<AgentStep>(`/agent-steps/${stepId}`, data);
}

export function deleteAgentStep(stepId: string) {
  return api.delete<MessageResponse>(`/agent-steps/${stepId}`);
}
