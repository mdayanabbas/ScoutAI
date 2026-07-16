"use client";

import { useState } from "react";

import { PageHeader } from "@/components/layout/PageHeader";
import {
  ActiveResumeCard,
  ParsedResumeSignals,
  ResumeLibrary,
} from "@/components/resume/ResumeCards";
import { ResumeUploadCard } from "@/components/resume/ResumeUploadCard";
import {
  useActivateResume,
  useActiveResume,
  useDeleteResume,
  useReparseResume,
  useResumes,
  useUploadResume,
} from "@/hooks/use-resumes";
import type { ResumeResponse } from "@/types/resume";

export default function ResumePage() {
  const resumesQuery = useResumes({ limit: 50 });
  const activeResumeQuery = useActiveResume();
  const uploadResume = useUploadResume();
  const activateResume = useActivateResume();
  const reparseResume = useReparseResume();
  const deleteResume = useDeleteResume();
  const [message, setMessage] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [pendingId, setPendingId] = useState<string | null>(null);
  const resumes = resumesQuery.data?.items ?? [];
  const activeResume = activeResumeQuery.data ?? null;

  async function handleUpload(file: File, makeActive: boolean) {
    setMessage(null);
    setActionError(null);
    try {
      const result = await uploadResume.mutateAsync({ file, makeActive });
      setMessage(
        result.warnings?.length
          ? `Resume uploaded with warnings: ${result.warnings.join(", ")}`
          : "Resume uploaded and parsed.",
      );
    } catch (error) {
      setActionError(error instanceof Error ? error.message : "Upload failed.");
    }
  }

  async function handleActivate(resume: ResumeResponse) {
    setPendingId(resume.id);
    setActionError(null);
    try {
      await activateResume.mutateAsync(resume.id);
      setMessage("Active resume updated.");
    } catch (error) {
      setActionError(error instanceof Error ? error.message : "Resume could not be activated.");
    } finally {
      setPendingId(null);
    }
  }

  async function handleReparse(resume: ResumeResponse) {
    setPendingId(resume.id);
    setActionError(null);
    try {
      await reparseResume.mutateAsync(resume.id);
      setMessage("Resume reparsed.");
    } catch (error) {
      setActionError(error instanceof Error ? error.message : "Resume could not be reparsed.");
    } finally {
      setPendingId(null);
    }
  }

  async function handleDelete(resume: ResumeResponse) {
    const label = resume.original_filename ?? resume.filename ?? "this resume";
    if (!window.confirm(`Delete ${label}?`)) {
      return;
    }
    setPendingId(resume.id);
    setActionError(null);
    try {
      await deleteResume.mutateAsync(resume.id);
      setMessage("Resume deleted.");
    } catch (error) {
      setActionError(error instanceof Error ? error.message : "Resume could not be deleted.");
    } finally {
      setPendingId(null);
    }
  }

  return (
    <>
      <PageHeader
        title="Resume"
        description="Upload your resume so ScoutAI can generate resume-aware application packets."
      />

      {message ? (
        <div className="mb-5 rounded-md border border-[#bbf7d0] bg-[#f0fdf4] p-4 text-sm text-[#166534]">
          {message}
        </div>
      ) : null}

      {actionError ? (
        <div className="mb-5 rounded-md border border-[#fecaca] bg-[#fff7f7] p-4 text-sm text-[#991b1b]">
          {actionError}
        </div>
      ) : null}

      {resumesQuery.error ? (
        <div className="mb-5 rounded-md border border-[#fecaca] bg-[#fff7f7] p-4 text-sm text-[#991b1b]">
          Resume library could not load.
        </div>
      ) : null}

      <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_360px]">
        <div className="space-y-5">
          <ActiveResumeCard
            resume={activeResume}
            pendingId={pendingId}
            onReparse={handleReparse}
            onDelete={handleDelete}
          />
          <ParsedResumeSignals resume={activeResume} />
          <ResumeLibrary
            resumes={resumes}
            pendingId={pendingId}
            onActivate={handleActivate}
            onReparse={handleReparse}
            onDelete={handleDelete}
          />
        </div>
        <ResumeUploadCard pending={uploadResume.isPending} onUpload={handleUpload} />
      </div>
    </>
  );
}
