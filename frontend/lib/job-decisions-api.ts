import { api, ApiError } from "@/lib/api";
import type {
  JobApplicationDecisionResponse,
  JobDecisionListParams,
  JobDecisionListResponse,
  JobDecisionPayload,
  JobDecisionStatus,
  JobDecisionStatusCounts,
} from "@/types/job-decision";

type LegacyDecisionPayload = {
  status?: string;
  notes?: string | null;
};

export async function saveJobDecision(
  jobId: string,
  payload: JobDecisionPayload,
) {
  return postWithCompatibility(`/job-decisions/jobs/${jobId}`, payload);
}

export async function getJobDecision(jobId: string) {
  try {
    const response = await api.get<JobApplicationDecisionResponse>(
      `/job-decisions/jobs/${jobId}`,
    );
    return normalizeDecision(response);
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) {
      return null;
    }
    throw error;
  }
}

export async function listJobDecisions(params: JobDecisionListParams = {}) {
  const response = await api.get<JobDecisionListResponse>("/job-decisions", {
    ...params,
    status: params.decision_status ?? params.status,
    decision_status: undefined,
  });
  return {
    ...response,
    items: (response.items ?? []).map(normalizeDecision),
  };
}

export async function getJobDecisionStatusCounts() {
  return api.get<JobDecisionStatusCounts>("/job-decisions/status-counts");
}

export async function updateJobDecision(
  decisionId: string,
  payload: JobDecisionPayload,
) {
  return patchWithCompatibility(`/job-decisions/${decisionId}`, payload);
}

export async function archiveJobDecision(decisionId: string) {
  const response = await api.post<JobApplicationDecisionResponse>(
    `/job-decisions/${decisionId}/archive`,
  );
  return normalizeDecision(response);
}

export async function deleteJobDecision(decisionId: string) {
  return api.delete<void>(`/job-decisions/${decisionId}`);
}

async function postWithCompatibility(path: string, payload: JobDecisionPayload) {
  try {
    const response = await api.post<JobApplicationDecisionResponse>(path, payload);
    return normalizeDecision(response, payload);
  } catch (error) {
    if (shouldRetryLegacy(error)) {
      const response = await api.post<JobApplicationDecisionResponse>(
        path,
        toLegacyPayload(payload),
      );
      return normalizeDecision(response, payload);
    }
    throw error;
  }
}

async function patchWithCompatibility(path: string, payload: JobDecisionPayload) {
  try {
    const response = await api.patch<JobApplicationDecisionResponse>(path, payload);
    return normalizeDecision(response, payload);
  } catch (error) {
    if (shouldRetryLegacy(error)) {
      const response = await api.patch<JobApplicationDecisionResponse>(
        path,
        toLegacyPayload(payload),
      );
      return normalizeDecision(response, payload);
    }
    throw error;
  }
}

function shouldRetryLegacy(error: unknown) {
  return error instanceof ApiError && error.status === 422;
}

function normalizeDecision<T extends JobApplicationDecisionResponse>(
  decision: T,
  requested?: JobDecisionPayload,
): T {
  const status = requested?.decision_status ?? decision.decision_status ?? decision.status;
  return {
    ...decision,
    decision_status: status,
    status,
    priority: requested?.priority ?? decision.priority ?? "medium",
    next_action: requested?.next_action ?? decision.next_action ?? null,
  };
}

function toLegacyPayload(payload: JobDecisionPayload): LegacyDecisionPayload {
  return {
    status: toLegacyStatus(payload.decision_status),
    notes: payload.notes ?? payload.next_action ?? null,
  };
}

function toLegacyStatus(status: JobDecisionStatus | undefined) {
  if (status === "applied") {
    return "applied";
  }
  if (status === "skipped" || status === "not_interested" || status === "rejected") {
    return "dismissed";
  }
  if (status === "archived") {
    return "archived";
  }
  return "interested";
}
