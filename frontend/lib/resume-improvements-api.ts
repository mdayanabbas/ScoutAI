import { api } from "@/lib/api";
import type {
  ResumeImprovementRequest,
  ResumeImprovementResponse,
} from "@/types/resume-improvement";

export const defaultResumeImprovementPayload = {
  update_decision: true,
  include_section_suggestions: true,
  include_bullet_suggestions: true,
  include_skill_gap_suggestions: true,
  include_project_reordering: true,
  include_remote_fit_suggestions: true,
} satisfies ResumeImprovementRequest;

export function generateResumeImprovementForJob(
  jobId: string,
  payload: ResumeImprovementRequest = {},
) {
  return api.post<ResumeImprovementResponse>(
    `/resume-improvements/jobs/${jobId}`,
    { ...defaultResumeImprovementPayload, ...payload },
  );
}

export function generateResumeImprovementForDecision(
  decisionId: string,
  payload: ResumeImprovementRequest = {},
) {
  return api.post<ResumeImprovementResponse>(
    `/resume-improvements/decisions/${decisionId}`,
    { ...defaultResumeImprovementPayload, ...payload },
  );
}
