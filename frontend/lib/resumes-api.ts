import { api, ApiError } from "@/lib/api";
import type {
  ResumeActivateResponse,
  ResumeListParams,
  ResumeListResponse,
  ResumeResponse,
  ResumeUploadResponse,
} from "@/types/resume";

export function uploadResume(file: File, makeActive = true) {
  const data = new FormData();
  data.append("file", file);
  data.append("make_active", String(makeActive));
  return api.post<ResumeUploadResponse>("/resumes/upload", data);
}

export function fetchResumes(params: ResumeListParams = {}) {
  return api.get<ResumeListResponse>("/resumes", params);
}

export async function fetchActiveResume() {
  try {
    return await api.get<ResumeResponse>("/resumes/active");
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) {
      return null;
    }
    throw error;
  }
}

export function fetchResume(resumeId: string) {
  return api.get<ResumeResponse>(`/resumes/${resumeId}`);
}

export function activateResume(resumeId: string) {
  return api.post<ResumeActivateResponse>(`/resumes/${resumeId}/activate`);
}

export function reparseResume(resumeId: string) {
  return api.post<ResumeUploadResponse>(`/resumes/${resumeId}/reparse`);
}

export function deleteResume(resumeId: string) {
  return api.delete<void>(`/resumes/${resumeId}`);
}
