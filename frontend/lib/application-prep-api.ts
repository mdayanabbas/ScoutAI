import { api, ApiError } from "@/lib/api";
import type {
  ApplicationPrepRequest,
  ApplicationPrepResponse,
} from "@/types/application-prep";

const defaultPrepPayload = {
  update_decision: true,
  include_cold_dm_angle: true,
  include_resume_focus: true,
  include_checklist: true,
} satisfies ApplicationPrepRequest;

export function generateApplicationPrepForJob(
  jobId: string,
  payload: ApplicationPrepRequest = {},
) {
  return api.post<ApplicationPrepResponse>(
    `/application-prep/jobs/${jobId}`,
    { ...defaultPrepPayload, ...payload },
  );
}

export function generateApplicationPrepForDecision(
  decisionId: string,
  payload: ApplicationPrepRequest = {},
) {
  return api.post<ApplicationPrepResponse>(
    `/application-prep/decisions/${decisionId}`,
    { ...defaultPrepPayload, ...payload },
  );
}

export async function getApplicationPrepForJob(jobId: string) {
  try {
    return await api.get<ApplicationPrepResponse>(`/application-prep/jobs/${jobId}`);
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) {
      return null;
    }
    throw error;
  }
}
