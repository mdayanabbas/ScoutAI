"use client";

import type { ResumeResponse } from "@/types/resume";
import {
  formatDate,
  formatFileSize,
  parseStatusLabel,
  parseStatusTone,
  stringFromUnknown,
} from "@/components/resume/resume-format";

export function ActiveResumeCard({
  resume,
  pendingId,
  onReparse,
  onDelete,
}: {
  resume?: ResumeResponse | null;
  pendingId?: string | null;
  onReparse: (resume: ResumeResponse) => void;
  onDelete: (resume: ResumeResponse) => void;
}) {
  return (
    <section className="rounded-md border border-[#d9dee8] bg-white p-5 shadow-sm">
      <h2 className="text-base font-semibold text-[#171923]">Active Resume</h2>
      {!resume ? (
        <div className="mt-3 rounded border border-dashed border-[#c8ced8] bg-[#fcfcfd] p-4">
          <p className="text-sm font-medium text-[#344054]">
            No active resume uploaded yet.
          </p>
          <p className="mt-1 text-sm text-[#667085]">
            Upload a resume to make application packets more accurate.
          </p>
        </div>
      ) : (
        <ResumeSummaryCard
          resume={resume}
          pendingId={pendingId}
          onReparse={onReparse}
          onDelete={onDelete}
          primary
        />
      )}
    </section>
  );
}

export function ResumeLibrary({
  resumes,
  pendingId,
  onActivate,
  onReparse,
  onDelete,
}: {
  resumes: ResumeResponse[];
  pendingId?: string | null;
  onActivate: (resume: ResumeResponse) => void;
  onReparse: (resume: ResumeResponse) => void;
  onDelete: (resume: ResumeResponse) => void;
}) {
  return (
    <section className="rounded-md border border-[#d9dee8] bg-white p-5 shadow-sm">
      <h2 className="text-base font-semibold text-[#171923]">Resume Library</h2>
      {resumes.length === 0 ? (
        <p className="mt-3 text-sm text-[#667085]">No resumes uploaded yet.</p>
      ) : (
        <div className="mt-4 space-y-3">
          {resumes.map((resume) => (
            <ResumeSummaryCard
              key={resume.id}
              resume={resume}
              pendingId={pendingId}
              onActivate={onActivate}
              onReparse={onReparse}
              onDelete={onDelete}
            />
          ))}
        </div>
      )}
    </section>
  );
}

function ResumeSummaryCard({
  resume,
  pendingId,
  onActivate,
  onReparse,
  onDelete,
  primary = false,
}: {
  resume: ResumeResponse;
  pendingId?: string | null;
  onActivate?: (resume: ResumeResponse) => void;
  onReparse: (resume: ResumeResponse) => void;
  onDelete: (resume: ResumeResponse) => void;
  primary?: boolean;
}) {
  const pending = pendingId === resume.id;
  return (
    <div className={["rounded border p-4", primary ? "border-[#bbf7d0] bg-[#f0fdf4]" : "border-[#edf0f5] bg-[#fcfcfd]"].join(" ")}>
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <span className={`rounded-full border px-2 py-0.5 text-xs font-medium ${parseStatusTone(resume.parse_status)}`}>
              {parseStatusLabel(resume.parse_status)}
            </span>
            {resume.is_active ? (
              <span className="rounded-full border border-[#bbf7d0] bg-white px-2 py-0.5 text-xs font-medium text-[#166534]">
                Active
              </span>
            ) : null}
          </div>
          <h3 className="mt-2 break-words text-sm font-semibold text-[#171923]">
            {resume.original_filename ?? resume.filename ?? "Resume"}
          </h3>
          <dl className="mt-2 grid gap-2 text-xs text-[#667085] sm:grid-cols-2 lg:grid-cols-4">
            <Metric label="Uploaded" value={formatDate(resume.created_at)} />
            <Metric label="Parsed" value={formatDate(resume.parsed_at)} />
            <Metric label="Size" value={formatFileSize(resume.file_size_bytes)} />
            <Metric label="Signals" value={`${resume.skills?.length ?? 0} skills, ${resume.technologies?.length ?? 0} tech, ${resume.projects?.length ?? 0} projects`} />
          </dl>
          {resume.parse_status === "failed" && resume.parse_error ? (
            <p className="mt-3 rounded border border-[#fecaca] bg-[#fff7f7] px-3 py-2 text-sm text-[#991b1b]">
              {resume.parse_error}
            </p>
          ) : null}
        </div>
        <div className="flex shrink-0 flex-wrap gap-2">
          {!resume.is_active && onActivate ? (
            <button
              type="button"
              onClick={() => onActivate(resume)}
              disabled={pending}
              className="rounded border border-[#166534] bg-white px-3 py-2 text-sm font-medium text-[#166534] hover:bg-[#f0fdf4] disabled:cursor-not-allowed disabled:opacity-60"
            >
              Make Active
            </button>
          ) : null}
          <button
            type="button"
            onClick={() => onReparse(resume)}
            disabled={pending}
            className="rounded border border-[#c8ced8] bg-white px-3 py-2 text-sm font-medium text-[#344054] hover:bg-[#f8fafc] disabled:cursor-not-allowed disabled:opacity-60"
          >
            Reparse
          </button>
          <button
            type="button"
            onClick={() => onDelete(resume)}
            disabled={pending}
            className="rounded border border-[#fecaca] bg-white px-3 py-2 text-sm font-medium text-[#991b1b] hover:bg-[#fff7f7] disabled:cursor-not-allowed disabled:opacity-60"
          >
            Delete
          </button>
        </div>
      </div>
    </div>
  );
}

export function ParsedResumeSignals({ resume }: { resume?: ResumeResponse | null }) {
  return (
    <section className="rounded-md border border-[#d9dee8] bg-white p-5 shadow-sm">
      <h2 className="text-base font-semibold text-[#171923]">Parsed Resume Signals</h2>
      {!resume ? (
        <p className="mt-3 text-sm text-[#667085]">Not detected yet.</p>
      ) : (
        <div className="mt-4 grid gap-3 lg:grid-cols-2">
          <SignalGroup title="Summary" values={summaryValues(resume)} />
          <SignalGroup title="Skills" values={resume.skills ?? []} />
          <SignalGroup title="Technologies" values={resume.technologies ?? []} />
          <SignalGroup title="Projects" values={(resume.projects ?? []).map(stringFromUnknown)} />
          <SignalGroup title="Experience" values={(resume.experience ?? []).map(stringFromUnknown)} />
          <SignalGroup title="Education" values={(resume.education ?? []).map(stringFromUnknown)} />
          <SignalGroup title="Certifications" values={(resume.certifications ?? []).map(stringFromUnknown)} />
          <SignalGroup title="Links" values={resume.links ?? []} />
        </div>
      )}
    </section>
  );
}

function SignalGroup({ title, values }: { title: string; values: string[] }) {
  return (
    <div className="rounded border border-[#edf0f5] bg-[#fcfcfd] p-3">
      <h3 className="text-xs font-semibold uppercase tracking-normal text-[#667085]">
        {title}
      </h3>
      {values.length > 0 ? (
        <div className="mt-2 flex flex-wrap gap-2">
          {values.slice(0, 18).map((value, index) => (
            <span
              key={`${title}-${value}-${index}`}
              className="rounded border border-[#d9dee8] bg-white px-2 py-1 text-xs text-[#344054]"
            >
              {value}
            </span>
          ))}
        </div>
      ) : (
        <p className="mt-2 text-sm text-[#98a2b3]">Not detected yet.</p>
      )}
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="font-medium text-[#475467]">{label}</dt>
      <dd>{value}</dd>
    </div>
  );
}

function summaryValues(resume: ResumeResponse) {
  const summary = resume.parsed_summary;
  if (!summary) {
    return [];
  }
  const text = summary.text;
  return typeof text === "string" && text.trim() ? [text] : [];
}
