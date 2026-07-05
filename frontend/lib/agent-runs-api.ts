import { api } from "@/lib/api";
import type { AgentRun, ListAgentRunsParams } from "@/types/agent-run";
import type { PaginatedResponse } from "@/types/common";

export function listAgentRuns(params: ListAgentRunsParams = {}) {
  return api.get<PaginatedResponse<AgentRun>>("/agent-runs", params);
}
