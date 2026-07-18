import { api } from "@/lib/api";
import { normalizeDiscoveryRunListResponse } from "@/lib/discovery-run-normalization";
import type {
  RemoteJobDiscoveryOrchestratorResult,
  RemoteJobDiscoveryPlan,
  RemoteJobDiscoveryRunRequest,
} from "@/types/discovery";

export function fetchRemoteDiscoveryPlan() {
  return api.get<RemoteJobDiscoveryPlan>("/discovery/remote-jobs/plan");
}

export function runRemoteJobDiscovery(payload: RemoteJobDiscoveryRunRequest) {
  return api.post<RemoteJobDiscoveryOrchestratorResult>(
    "/discovery/remote-jobs/run",
    payload,
  );
}

export async function fetchDiscoveryRuns(params: {
  limit?: number;
  offset?: number;
  source?: string;
  status?: string;
} = {}) {
  const response = await api.get<unknown>("/discovery/runs", params);
  return normalizeDiscoveryRunListResponse(response);
}

export function fetchDiscoveryRun(runId: string) {
  return api.get<unknown>(`/discovery/runs/${runId}`);
}
