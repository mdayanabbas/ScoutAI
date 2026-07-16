"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useMemo, useState, type ReactNode } from "react";
import { useQuery } from "@tanstack/react-query";

import { ApplicationPacketPanel } from "@/components/applications/ApplicationPacketPanel";
import { ApplicationPrepPanel } from "@/components/applications/ApplicationPrepPanel";
import { ResumeGapAnalysis } from "@/components/applications/ResumeGapAnalysis";
import { ResumeImprovementPanel } from "@/components/applications/ResumeImprovementPanel";
import { PageHeader } from "@/components/layout/PageHeader";
import { decisionStatusLabel } from "@/components/recommendations/RecommendedJobCard";
import {
  formatExperience,
  formatMatchTier,
  formatRemoteEligibility,
  formatSalary,
  labelize,
  normalizeExternalUrl,
  sourceAttribution,
} from "@/components/recommendations/recommendation-format";
import { useActiveResume } from "@/hooks/use-resumes";
import { generateApplicationPacketForDecision, generateApplicationPacketForJob } from "@/lib/application-packet-api";
import { generateApplicationPrepForDecision, generateApplicationPrepForJob } from "@/lib/application-prep-api";
import {
  buildApplicationWorkspaceMarkdown,
  buildWorkspaceMarkdownFilename,
} from "@/lib/application-workspace-markdown";
import { getJobDecision, listJobDecisions, saveJobDecision, updateJobDecision } from "@/lib/job-decisions-api";
import { fetchRecommendedJobMatches } from "@/lib/job-matches-api";
import { getJob } from "@/lib/jobs-api";
import { generateResumeImprovementForDecision, generateResumeImprovementForJob } from "@/lib/resume-improvements-api";
import type { ApplicationPacketResponse } from "@/types/application-packet";
import type { ApplicationPrepResponse } from "@/types/application-prep";
import type { Job } from "@/types/job";
import type { JobApplicationDecisionResponse, JobDecisionListItem, JobDecisionPayload } from "@/types/job-decision";
import type { RecommendedJobMatch } from "@/types/job-match";
import type { ResumeImprovementResponse } from "@/types/resume-improvement";

const checklistDefaults = [
  "Review job requirements",
  "Check resume gaps",
  "Improve resume bullets",
  "Generate application packet",
  "Apply through official link",
  "Mark as applied",
];

export default function JobWorkspacePage() {
  const params = useParams<{ jobId: string }>();
  const jobId = params.jobId;
  const jobQuery = useQuery({ queryKey: ["job-workspace", "job", jobId], queryFn: () => getJob(jobId), enabled: Boolean(jobId) });
  const recommendationQuery = useQuery({
    queryKey: ["job-workspace", "recommendations", jobId],
    queryFn: () => fetchRecommendedJobMatches({ limit: 100, include_remote_unknown: true, include_unsuitable: true }),
    enabled: Boolean(jobId),
  });
  const trackedQuery = useQuery({
    queryKey: ["job-workspace", "tracked", jobId],
    queryFn: () => listJobDecisions({ limit: 100, include_archived: true }),
    enabled: Boolean(jobId),
  });
  const decisionQuery = useQuery({
    queryKey: ["job-workspace", "decision", jobId],
    queryFn: () => getJobDecision(jobId),
    enabled: Boolean(jobId),
  });
  const activeResumeQuery = useActiveResume();
  const [decision, setDecision] = useState<JobApplicationDecisionResponse | null>(null);
  const currentDecision = decision ?? decisionQuery.data ?? trackedQuery.data?.items.find((item) => item.job_id === jobId) ?? null;
  const recommendedMatch = recommendationQuery.data?.items.find((item) => item.job_id === jobId) ?? null;
  const trackedMatch = trackedQuery.data?.items.find((item) => item.job_id === jobId) ?? null;
  const job = jobQuery.data ?? null;
  const hasWorkspaceSource = Boolean(job || recommendedMatch || trackedMatch);
  const [packet, setPacket] = useState<ApplicationPacketResponse | null>(null);
  const [prep, setPrep] = useState<ApplicationPrepResponse | null>(null);
  const [improvement, setImprovement] = useState<ResumeImprovementResponse | null>(null);
  const [pendingTool, setPendingTool] = useState<string | null>(null);
  const [toolError, setToolError] = useState<string | null>(null);
  const [notesDraft, setNotesDraft] = useState("");
  const [editingNotes, setEditingNotes] = useState(false);
  const [decisionPending, setDecisionPending] = useState(false);
  const [decisionError, setDecisionError] = useState<string | null>(null);
  const [checked, setChecked] = useState<Record<string, boolean>>({});
  const [exportMessage, setExportMessage] = useState<string | null>(null);

  const display = useMemo(
    () => workspaceDisplay(job, recommendedMatch, trackedMatch),
    [job, recommendedMatch, trackedMatch],
  );
  const applyUrl = normalizeExternalUrl(display.applyUrl) ?? normalizeExternalUrl(display.jobUrl);
  const attribution = sourceAttribution(display.jobUrl);
  const visibleNotes = editingNotes ? notesDraft : currentDecision?.notes ?? "";
  const checklistItems = checklistDefaults.map((label) => ({ label, checked: Boolean(checked[label]) }));

  function buildMarkdown() {
    return buildApplicationWorkspaceMarkdown({
      job: {
        title: display.title,
        companyName: display.companyName,
        role: labelize(display.roleCategory) || display.title,
        source: attribution.label.replace("Source: ", ""),
        applyUrl,
        matchTier: formatMatchTier(display.matchTier),
        totalScore: display.totalScore,
        remoteEligibility: formatRemoteEligibility(display.remoteEligibility),
        decisionStatus: currentDecision?.decision_status ?? currentDecision?.status ?? null,
      },
      activeResume: activeResumeQuery.data ?? null,
      packet,
      improvement,
      prep,
      checklist: checklistItems,
      notes: visibleNotes,
    });
  }

  async function copyMarkdown() {
    try {
      await navigator.clipboard.writeText(buildMarkdown());
      setExportMessage("Copied workspace Markdown.");
    } catch {
      setExportMessage("Could not copy Markdown.");
    }
  }

  function downloadMarkdown() {
    try {
      const blob = new Blob([buildMarkdown()], { type: "text/markdown;charset=utf-8" });
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = buildWorkspaceMarkdownFilename(display.companyName, display.title);
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      URL.revokeObjectURL(url);
      setExportMessage("Downloaded workspace Markdown.");
    } catch {
      setExportMessage("Could not download Markdown.");
    }
  }

  async function ensureDecision(payload: JobDecisionPayload) {
    setDecisionPending(true);
    setDecisionError(null);
    try {
      const updated = currentDecision?.id
        ? await updateJobDecision(currentDecision.id, payload)
        : await saveJobDecision(jobId, payload);
      setDecision(updated);
      await decisionQuery.refetch();
      await trackedQuery.refetch();
    } catch (error) {
      setDecisionError(error instanceof Error ? error.message : "Decision could not be updated.");
    } finally {
      setDecisionPending(false);
    }
  }

  async function saveNotes() {
    await ensureDecision({ notes: notesDraft });
    setEditingNotes(false);
  }

  async function generatePacket() {
    await runTool("packet", async () => {
      const result = currentDecision?.id
        ? await generateApplicationPacketForDecision(currentDecision.id)
        : await generateApplicationPacketForJob(jobId);
      setPacket(result);
      if (result.decision_id) {
        await decisionQuery.refetch();
        await trackedQuery.refetch();
      }
    });
  }

  async function generateImprovement() {
    await runTool("improvement", async () => {
      const result = currentDecision?.id
        ? await generateResumeImprovementForDecision(currentDecision.id)
        : await generateResumeImprovementForJob(jobId);
      setImprovement(result);
      if (result.decision_id) {
        await decisionQuery.refetch();
        await trackedQuery.refetch();
      }
    });
  }

  async function generatePrep() {
    await runTool("prep", async () => {
      const result = currentDecision?.id
        ? await generateApplicationPrepForDecision(currentDecision.id)
        : await generateApplicationPrepForJob(jobId);
      setPrep(result);
      if (result.decision_id) {
        await decisionQuery.refetch();
        await trackedQuery.refetch();
      }
    });
  }

  async function runTool(name: string, action: () => Promise<void>) {
    setPendingTool(name);
    setToolError(null);
    try {
      await action();
    } catch (error) {
      setToolError(error instanceof Error ? error.message : "Workspace tool failed.");
    } finally {
      setPendingTool(null);
    }
  }

  if ((jobQuery.isLoading || recommendationQuery.isLoading || trackedQuery.isLoading) && !hasWorkspaceSource) {
    return <LoadingState />;
  }

  if (!hasWorkspaceSource) {
    return (
      <>
        <PageHeader title="Application Workspace" description="Job details could not be found in the current ScoutAI data." />
        <div className="rounded-md border border-[#fecaca] bg-[#fff7f7] p-4 text-sm text-[#991b1b]">
          Missing job. Refresh recommendations or tracked jobs, then try again.
        </div>
      </>
    );
  }

  return (
    <>
      <PageHeader
        title={display.title}
        description={`${display.companyName ?? "Unknown company"} application workspace.`}
        actions={
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              onClick={copyMarkdown}
              className="rounded border border-[#c8ced8] bg-white px-3 py-2 text-sm font-medium text-[#344054] hover:bg-[#f8fafc]"
            >
              Copy Markdown
            </button>
            <button
              type="button"
              onClick={downloadMarkdown}
              className="rounded border border-[#c8ced8] bg-white px-3 py-2 text-sm font-medium text-[#344054] hover:bg-[#f8fafc]"
            >
              Download Markdown
            </button>
            {applyUrl ? (
              <a href={applyUrl} target="_blank" rel="noopener noreferrer" className="rounded bg-[#172033] px-3 py-2 text-sm font-medium text-white hover:bg-[#0f1728]">
                Apply / View Job
              </a>
            ) : null}
          </div>
        }
      />

      {exportMessage ? (
        <div className="mb-4 rounded-md border border-[#d9dee8] bg-white px-4 py-3 text-sm text-[#344054]">
          {exportMessage}
        </div>
      ) : null}

      <section className="mb-5 rounded-md border border-[#d9dee8] bg-white p-5">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <div className="flex flex-wrap gap-2">
              <Badge>{formatMatchTier(display.matchTier)}</Badge>
              <Badge>{formatRemoteEligibility(display.remoteEligibility)}</Badge>
              <Badge>{currentDecision ? decisionStatusLabel(currentDecision.decision_status ?? currentDecision.status ?? "interested") : "Not tracked yet"}</Badge>
              {display.totalScore != null ? <Badge>{`Score ${Math.round(display.totalScore)}`}</Badge> : null}
            </div>
            <dl className="mt-4 grid gap-3 text-sm sm:grid-cols-2 xl:grid-cols-4">
              <Fact label="Company" value={display.companyName ?? "Unknown company"} />
              <Fact label="Role" value={labelize(display.roleCategory)} />
              <Fact label="Experience" value={formatExperience(display)} />
              <Fact label="Salary" value={formatSalary(display) ?? "No salary listed"} />
              <Fact label="Source" value={attribution.label.replace("Source: ", "")} />
              <Fact label="Published" value={formatDate(display.publishedAt)} />
              <Fact label="Location" value={display.location ?? "Location not specified"} />
              <Fact label="Seniority" value={labelize(display.seniority)} />
            </dl>
          </div>
        </div>
      </section>

      <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_360px]">
        <main className="space-y-5">
          <WorkspaceSection title="Overview">
            <p className="text-sm leading-6 text-[#344054]">
              {display.eligibilityReason ?? "Review this role against your profile, resume evidence and current application status."}
            </p>
          </WorkspaceSection>

          <WorkspaceSection title="Application Packet" action={<ToolButton pending={pendingTool === "packet"} label={packet ? "Regenerate Application Packet" : "Generate Application Packet"} pendingLabel="Generating packet..." onClick={generatePacket} />}>
            {!packet ? <EmptyToolState text="Generate an application packet to organize apply steps and compare this job with your active resume." /> : <ApplicationPacketPanel packet={packet} />}
          </WorkspaceSection>

          <WorkspaceSection title="Resume Improvements" action={<ToolButton pending={pendingTool === "improvement"} label={improvement ? "Regenerate Resume Suggestions" : "Improve Resume for This Job"} pendingLabel="Generating resume suggestions..." onClick={generateImprovement} />}>
            {!improvement ? <EmptyToolState text="Generate resume improvement suggestions before tailoring your resume." /> : <ResumeImprovementPanel improvement={improvement} />}
          </WorkspaceSection>

          <WorkspaceSection title="Application Prep" action={<ToolButton pending={pendingTool === "prep"} label={prep ? "Regenerate Prep Notes" : "Prepare Application"} pendingLabel="Preparing..." onClick={generatePrep} />}>
            {!prep ? <EmptyToolState text="Prepare concise fit notes, talking points and checklist items." /> : <ApplicationPrepPanel prep={prep} />}
          </WorkspaceSection>

          <WorkspaceSection title="Resume Gaps">
            {packet ? (
              <ResumeGapAnalysis
                resumeUsed={packet.resume_used}
                resumeMatchSummary={packet.resume_match_summary}
                resumeStrengths={packet.resume_strengths}
                resumeGaps={packet.resume_gaps}
                resumeBulletSources={packet.resume_bullet_sources}
              />
            ) : activeResumeQuery.data ? (
              <EmptyToolState text="Generate an application packet to compare this job with your active resume." />
            ) : (
              <div className="rounded border border-[#fed7aa] bg-[#fff7ed] p-3 text-sm text-[#9a3412]">
                Upload a resume to enable resume-aware gap analysis. <Link href="/profile/resume" className="font-medium underline">Upload Resume</Link>
              </div>
            )}
          </WorkspaceSection>

          {toolError ? (
            <div className="rounded border border-[#fecaca] bg-[#fff7f7] p-3 text-sm text-[#991b1b]">
              {toolError}
            </div>
          ) : null}
        </main>

        <aside className="space-y-5">
          <DecisionControls decision={currentDecision} pending={decisionPending} onUpdate={ensureDecision} error={decisionError} />
          <ActiveResumeCard resume={activeResumeQuery.data} loading={activeResumeQuery.isLoading} />
          <Checklist checked={checked} onToggle={(item) => setChecked((current) => ({ ...current, [item]: !current[item] }))} />
          <NotesCard
            notes={currentDecision?.notes ?? ""}
            draft={notesDraft}
            editing={editingNotes}
            pending={decisionPending}
            onStart={() => {
              setNotesDraft(currentDecision?.notes ?? "");
              setEditingNotes(true);
            }}
            onChange={setNotesDraft}
            onSave={saveNotes}
            onCancel={() => setEditingNotes(false)}
          />
          {applyUrl ? (
            <a href={applyUrl} target="_blank" rel="noopener noreferrer" className="block rounded bg-[#172033] px-3 py-2 text-center text-sm font-medium text-white hover:bg-[#0f1728]">
              Apply / View Job
            </a>
          ) : null}
        </aside>
      </div>
    </>
  );
}

function DecisionControls({ decision, pending, onUpdate, error }: { decision: JobApplicationDecisionResponse | null; pending: boolean; onUpdate: (payload: JobDecisionPayload) => void; error: string | null }) {
  const actions: Array<[string, JobDecisionPayload]> = [
    ["Save", { decision_status: "saved", priority: "medium" }],
    ["Interested", { decision_status: "interested", priority: "medium" }],
    ["Needs Resume", { decision_status: "needs_custom_resume", priority: "high", next_action: "Tailor resume for this role." }],
    ["Applied", { decision_status: "applied", priority: "high" }],
    ["Skipped", { decision_status: "skipped" }],
    ["Not Interested", { decision_status: "not_interested" }],
    ["Archive", { decision_status: "archived" }],
  ];
  return (
    <section className="rounded-md border border-[#d9dee8] bg-white p-4">
      <h2 className="text-sm font-semibold text-[#171923]">Decision</h2>
      <p className="mt-1 text-sm text-[#667085]">
        {decision ? decisionStatusLabel(decision.decision_status ?? decision.status ?? "interested") : "Not tracked yet"}
      </p>
      <div className="mt-3 flex flex-wrap gap-2">
        {actions.map(([label, payload]) => (
          <button key={label} type="button" disabled={pending} onClick={() => onUpdate(payload)} className="rounded border border-[#c8ced8] bg-white px-3 py-1.5 text-sm font-medium text-[#344054] hover:bg-[#f8fafc] disabled:cursor-not-allowed disabled:opacity-60">
            {label}
          </button>
        ))}
      </div>
      {error ? <p className="mt-3 text-sm text-[#991b1b]">{error}</p> : null}
    </section>
  );
}

function ActiveResumeCard({ resume, loading }: { resume?: { original_filename?: string | null; parse_status?: string | null } | null; loading: boolean }) {
  return (
    <section className="rounded-md border border-[#d9dee8] bg-white p-4">
      <h2 className="text-sm font-semibold text-[#171923]">Active Resume</h2>
      {loading ? <p className="mt-2 text-sm text-[#667085]">Checking resume...</p> : null}
      {!loading && resume?.parse_status === "parsed" ? (
        <div className="mt-2">
          <Badge>Resume-aware enabled</Badge>
          <p className="mt-2 text-sm text-[#344054]">{resume.original_filename ?? "Active resume"}</p>
        </div>
      ) : null}
      {!loading && resume?.parse_status === "failed" ? (
        <p className="mt-2 text-sm text-[#991b1b]">Resume parsing failed. Reparse or upload another resume.</p>
      ) : null}
      {!loading && !resume ? (
        <p className="mt-2 text-sm text-[#667085]">No active resume uploaded.</p>
      ) : null}
      <Link href="/profile/resume" className="mt-3 inline-block rounded border border-[#c8ced8] px-3 py-2 text-sm font-medium text-[#344054] hover:bg-[#f8fafc]">
        Upload Resume
      </Link>
    </section>
  );
}

function Checklist({ checked, onToggle }: { checked: Record<string, boolean>; onToggle: (item: string) => void }) {
  return (
    <section className="rounded-md border border-[#d9dee8] bg-white p-4">
      <h2 className="text-sm font-semibold text-[#171923]">Apply Checklist</h2>
      <div className="mt-3 space-y-2">
        {checklistDefaults.map((item) => (
          <label key={item} className="flex items-center gap-2 text-sm text-[#344054]">
            <input type="checkbox" checked={Boolean(checked[item])} onChange={() => onToggle(item)} className="h-4 w-4 rounded border-[#c8ced8]" />
            {item}
          </label>
        ))}
      </div>
    </section>
  );
}

function NotesCard({ notes, draft, editing, pending, onStart, onChange, onSave, onCancel }: { notes: string; draft: string; editing: boolean; pending: boolean; onStart: () => void; onChange: (value: string) => void; onSave: () => void; onCancel: () => void }) {
  return (
    <section className="rounded-md border border-[#d9dee8] bg-white p-4">
      <h2 className="text-sm font-semibold text-[#171923]">Notes</h2>
      {editing ? (
        <>
          <textarea value={draft} onChange={(event) => onChange(event.target.value)} rows={5} className="mt-3 w-full rounded border border-[#c8ced8] px-3 py-2 text-sm" />
          <div className="mt-3 flex gap-2">
            <button type="button" disabled={pending} onClick={onSave} className="rounded bg-[#172033] px-3 py-2 text-sm font-medium text-white disabled:opacity-60">Save notes</button>
            <button type="button" disabled={pending} onClick={onCancel} className="rounded border border-[#c8ced8] px-3 py-2 text-sm font-medium text-[#344054]">Cancel</button>
          </div>
        </>
      ) : (
        <>
          <p className="mt-2 whitespace-pre-wrap text-sm text-[#344054]">{notes || "No notes yet."}</p>
          <button type="button" onClick={onStart} className="mt-3 rounded border border-[#c8ced8] px-3 py-2 text-sm font-medium text-[#344054] hover:bg-[#f8fafc]">Edit notes</button>
        </>
      )}
    </section>
  );
}

function WorkspaceSection({ title, action, children }: { title: string; action?: ReactNode; children: ReactNode }) {
  return (
    <section className="rounded-md border border-[#d9dee8] bg-white p-5 shadow-sm">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <h2 className="text-base font-semibold text-[#171923]">{title}</h2>
        {action}
      </div>
      <div className="mt-4">{children}</div>
    </section>
  );
}

function ToolButton({ pending, label, pendingLabel, onClick }: { pending: boolean; label: string; pendingLabel: string; onClick: () => void }) {
  return (
    <button type="button" disabled={pending} onClick={onClick} className="rounded bg-[#172033] px-3 py-2 text-sm font-medium text-white hover:bg-[#0f1728] disabled:cursor-not-allowed disabled:opacity-60">
      {pending ? pendingLabel : label}
    </button>
  );
}

function EmptyToolState({ text }: { text: string }) {
  return <p className="rounded border border-[#edf0f5] bg-[#fcfcfd] px-3 py-2 text-sm text-[#667085]">{text}</p>;
}

function Badge({ children }: { children: string }) {
  return <span className="rounded-full border border-[#d9dee8] bg-[#f8fafc] px-2 py-0.5 text-xs font-medium text-[#475467]">{children}</span>;
}

function Fact({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-xs font-medium uppercase tracking-normal text-[#667085]">{label}</dt>
      <dd className="mt-1 text-[#344054]">{value}</dd>
    </div>
  );
}

function LoadingState() {
  return (
    <>
      <PageHeader title="Application Workspace" description="Loading job workspace..." />
      <div className="h-64 animate-pulse rounded-md border border-[#d9dee8] bg-white" />
    </>
  );
}

type WorkspaceDisplay = {
  id: string;
  title: string;
  companyName?: string | null;
  companyId?: string | null;
  roleCategory?: string | null;
  location?: string | null;
  seniority?: string | null;
  experience_min?: number | null;
  experience_max?: number | null;
  salary_min?: number | string | null;
  salary_max?: number | string | null;
  salary_currency?: string | null;
  matchTier?: string | null;
  totalScore?: number | null;
  remoteEligibility?: string | null;
  eligibilityReason?: string | null;
  publishedAt?: string | null;
  jobUrl?: string | null;
  applyUrl?: string | null;
};

function workspaceDisplay(job?: Job | null, recommended?: RecommendedJobMatch | null, decision?: JobDecisionListItem | null): WorkspaceDisplay {
  return {
    id: job?.id ?? recommended?.job_id ?? decision?.job_id ?? "",
    title: job?.title ?? recommended?.title ?? decision?.title ?? decision?.job_title ?? "Job",
    companyName: job?.company_name ?? recommended?.company_name ?? decision?.company_name ?? null,
    companyId: job?.company_id ?? recommended?.company_id ?? decision?.company_id ?? null,
    roleCategory: job?.role_category ?? recommended?.role_category ?? null,
    location: job?.location ?? recommended?.location ?? null,
    seniority: recommended?.seniority ?? null,
    experience_min: job?.experience_min ?? recommended?.experience_min ?? null,
    experience_max: job?.experience_max ?? recommended?.experience_max ?? null,
    salary_min: job?.salary_min ?? recommended?.salary_min ?? decision?.salary_min ?? null,
    salary_max: job?.salary_max ?? recommended?.salary_max ?? decision?.salary_max ?? null,
    salary_currency: job?.salary_currency ?? recommended?.salary_currency ?? decision?.salary_currency ?? null,
    matchTier: recommended?.match_tier ?? decision?.match_tier ?? null,
    totalScore: recommended?.total_score ?? decision?.total_score ?? null,
    remoteEligibility: recommended?.remote_eligibility ?? decision?.remote_eligibility ?? job?.remote_type ?? null,
    eligibilityReason: recommended?.eligibility_reason ?? decision?.eligibility_reason ?? null,
    publishedAt: recommended?.published_at ?? null,
    jobUrl: job?.job_url ?? recommended?.job_url ?? decision?.job_url ?? null,
    applyUrl: recommended?.apply_url ?? decision?.apply_url ?? null,
  };
}

function formatDate(value?: string | null) {
  if (!value) return "Not listed";
  return new Intl.DateTimeFormat("en", { dateStyle: "medium" }).format(new Date(value));
}
