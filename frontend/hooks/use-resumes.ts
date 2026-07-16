import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  activateResume,
  deleteResume,
  fetchActiveResume,
  fetchResume,
  fetchResumes,
  reparseResume,
  uploadResume,
} from "@/lib/resumes-api";
import type { ResumeListParams } from "@/types/resume";

export const resumeKeys = {
  all: ["resumes"] as const,
  list: (params: ResumeListParams = {}) => [...resumeKeys.all, "list", params] as const,
  active: () => [...resumeKeys.all, "active"] as const,
  detail: (id: string) => [...resumeKeys.all, "detail", id] as const,
};

export function useResumes(params: ResumeListParams = {}) {
  return useQuery({
    queryKey: resumeKeys.list(params),
    queryFn: () => fetchResumes(params),
  });
}

export function useActiveResume() {
  return useQuery({
    queryKey: resumeKeys.active(),
    queryFn: fetchActiveResume,
    retry: 1,
  });
}

export function useResume(resumeId: string) {
  return useQuery({
    queryKey: resumeKeys.detail(resumeId),
    queryFn: () => fetchResume(resumeId),
    enabled: Boolean(resumeId),
  });
}

export function useUploadResume() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ file, makeActive }: { file: File; makeActive: boolean }) =>
      uploadResume(file, makeActive),
    onSuccess: () => invalidateResumes(queryClient),
  });
}

export function useActivateResume() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: activateResume,
    onSuccess: () => invalidateResumes(queryClient),
  });
}

export function useReparseResume() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: reparseResume,
    onSuccess: () => invalidateResumes(queryClient),
  });
}

export function useDeleteResume() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: deleteResume,
    onSuccess: () => invalidateResumes(queryClient),
  });
}

function invalidateResumes(queryClient: ReturnType<typeof useQueryClient>) {
  queryClient.invalidateQueries({ queryKey: resumeKeys.all });
}
