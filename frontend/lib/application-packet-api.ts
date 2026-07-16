import { api } from "@/lib/api";
import type {
  ApplicationPacketRequest,
  ApplicationPacketResponse,
} from "@/types/application-packet";

export const defaultApplicationPacketPayload = {
  update_decision: true,
  include_resume_bullets: true,
  include_cover_note_outline: true,
  include_cold_dm_outline: true,
  include_checklist: true,
  include_risk_review: true,
} satisfies ApplicationPacketRequest;

export function generateApplicationPacketForJob(
  jobId: string,
  payload: ApplicationPacketRequest = {},
) {
  return api.post<ApplicationPacketResponse>(
    `/application-packets/jobs/${jobId}`,
    { ...defaultApplicationPacketPayload, ...payload },
  );
}

export function generateApplicationPacketForDecision(
  decisionId: string,
  payload: ApplicationPacketRequest = {},
) {
  return api.post<ApplicationPacketResponse>(
    `/application-packets/decisions/${decisionId}`,
    { ...defaultApplicationPacketPayload, ...payload },
  );
}
