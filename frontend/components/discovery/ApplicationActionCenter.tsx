"use client";

import Link from "next/link";
import { useState } from "react";
import type { ReactNode } from "react";

import { ApplicationPacketPanel } from "@/components/applications/ApplicationPacketPanel";
import { ApplicationPrepPanel } from "@/components/applications/ApplicationPrepPanel";
import { ResumeImprovementPanel } from "@/components/applications/ResumeImprovementPanel";
import {
  formatMatchTier,
  formatRemoteEligibility,
  formatSalary,
  normalizeExternalUrl,
} from "@/components/recommendations/recommendation-format";
import {
  buildApplicationExportFilename,
  buildApplicationExportMarkdown,
  copyApplicationPackMarkdown,
  downloadMarkdownFile,
} from "@/lib/application-export-pack";
import { generateApplicationPacketForJob } from "@/lib/application-packet-api";
import { generateApplicationPrepForJob } from "@/lib/application-prep-api";
import { watchCompanyFromJob } from "@/lib/company-watchlist-api";
import { saveJobDecision, updateJobDecision } from "@/lib/job-decisions-api";
import { generateResumeImprovementForJob } from "@/lib/resume-improvements-api";
import { deriveResumeFitFromPacket, type ResumeFitResult } from "@/lib/resume-aware-review-ranking";
import type { ApplicationPacketResponse } from "@/types/application-packet";
import type { ApplicationPrepResponse } from "@/types/application-prep";
import type { CompanyWatchlistResponse } from "@/types/company-watchlist";
import type { JobApplicationDecisionResponse, JobDecisionStatus } from "@/types/job-decision";
import type { ResumeResponse } from "@/types/resume";
import type { ResumeImprovementResponse } from "@/types/resume-improvement";
import type { DailyScoutReviewItem } from "@/lib/daily-scout-review-queue";

const decisionActions: Array<[string, JobDecisionStatus]> = [
  ["Save", "saved"],
  ["Interested", "interested"],
  ["Applied", "applied"],
  ["Needs Resume", "needs_custom_resume"],
  ["Needs Cold DM", "needs_cold_dm"],
  ["Skip", "skipped"],
  ["Not Interested", "not_interested"],
];

export function ApplicationActionCenter({
  reviewItem,
  activeResume,
  existingDecision,
  existingWatchlistItem,
  resumeFitResult,
  onDecisionUpdated,
  onWatchCompanyUpdated,
  onResumeFitUpdated,
  onClose,
}: {
  reviewItem: DailyScoutReviewItem;
  activeResume?: ResumeResponse | null;
  existingDecision?: JobApplicationDecisionResponse | null;
  existingWatchlistItem?: CompanyWatchlistResponse | null;
  resumeFitResult?: ResumeFitResult | null;
  onDecisionUpdated?: (decision: JobApplicationDecisionResponse) => void;
  onWatchCompanyUpdated?: (watchlistItem: CompanyWatchlistResponse | null) => void;
  onResumeFitUpdated?: (result: ResumeFitResult) => void;
  onClose: () => void;
}) {
  const [packet, setPacket] = useState<ApplicationPacketResponse | null>(null);
  const [improvement, setImprovement] = useState<ResumeImprovementResponse | null>(null);
  const [prep, setPrep] = useState<ApplicationPrepResponse | null>(null);
  const [fit, setFit] = useState<ResumeFitResult | null>(resumeFitResult ?? null);
  const [decision, setDecision] = useState<JobApplicationDecisionResponse | null>(existingDecision ?? reviewItem.decision ?? null);
  const [watchlistItem, setWatchlistItem] = useState<CompanyWatchlistResponse | null>(existingWatchlistItem ?? null);
  const [loading, setLoading] = useState<Record<string, boolean>>({});
  const [errors, setErrors] = useState<Record<string, string | null>>({});
  const [copyMessage, setCopyMessage] = useState<string | null>(null);
  const [exportMessage, setExportMessage] = useState<string | null>(null);
  const [exportWarning, setExportWarning] = useState<string | null>(null);
  const [previewOpen, setPreviewOpen] = useState(false);

  const jobUrl = normalizeExternalUrl(reviewItem.job_url);
  const applyUrl = normalizeExternalUrl(reviewItem.apply_url);
  const salary = formatSalary({
    salary_min: reviewItem.salary_min,
    salary_max: reviewItem.salary_max,
    salary_currency: reviewItem.salary_currency,
  });
  const nextAction = recommendedNextAction(reviewItem, fit, decision);
  const exportMarkdown = buildExportMarkdown();
  const exportFilename = buildApplicationExportFilename(reviewItem);
  const missingMaterials = [
    !packet ? "application packet" : null,
    !improvement ? "resume improvements" : null,
    !prep ? "prep notes" : null,
  ].filter(Boolean);

  async function runSection<T>(key: string, task: () => Promise<T>, onSuccess: (value: T) => void) {
    setLoading((current) => ({ ...current, [key]: true }));
    setErrors((current) => ({ ...current, [key]: null }));
    try {
      const value = await task();
      onSuccess(value);
    } catch (error) {
      setErrors((current) => ({ ...current, [key]: friendlyError(error) }));
    } finally {
      setLoading((current) => ({ ...current, [key]: false }));
    }
  }

  function generatePacket() {
    if (!reviewItem.job_id) return;
    void runSection(
      "packet",
      fetchPacket,
      setPacket,
    );
  }

  function generateImprovement() {
    if (!reviewItem.job_id) return;
    void runSection(
      "improvement",
      fetchImprovement,
      setImprovement,
    );
  }

  function generatePrep() {
    if (!reviewItem.job_id) return;
    void runSection(
      "prep",
      fetchPrep,
      setPrep,
    );
  }

  function fetchPacket() {
    return generateApplicationPacketForJob(reviewItem.job_id, {
      update_decision: false,
      include_resume_bullets: true,
      include_cover_note_outline: true,
      include_cold_dm_outline: true,
      include_checklist: true,
      include_risk_review: true,
    });
  }

  function fetchImprovement() {
    return generateResumeImprovementForJob(reviewItem.job_id, {
      update_decision: false,
      include_section_suggestions: true,
      include_bullet_suggestions: true,
      include_skill_gap_suggestions: true,
      include_project_reordering: true,
      include_remote_fit_suggestions: true,
    });
  }

  function fetchPrep() {
    return generateApplicationPrepForJob(reviewItem.job_id, { update_decision: false });
  }

  function rankWithResume() {
    if (!reviewItem.job_id) return;
    if (!activeResume) {
      setErrors((current) => ({ ...current, resumeFit: "No active resume found. Upload or activate a resume first." }));
      return;
    }
    if (activeResume.parse_status === "failed") {
      setErrors((current) => ({ ...current, resumeFit: "Active resume parsing failed. Upload or activate a parsed resume first." }));
      return;
    }
    void runSection(
      "resumeFit",
      async () => {
        const generatedPacket = packet ?? await generateApplicationPacketForJob(reviewItem.job_id, {
          update_decision: false,
          include_resume_bullets: true,
          include_cover_note_outline: false,
          include_cold_dm_outline: false,
          include_checklist: true,
          include_risk_review: true,
        });
        const generatedImprovement = improvement ?? await generateResumeImprovementForJob(reviewItem.job_id, {
          update_decision: false,
          include_section_suggestions: true,
          include_bullet_suggestions: true,
          include_skill_gap_suggestions: true,
          include_project_reordering: true,
          include_remote_fit_suggestions: true,
        }).catch(() => null);
        if (!packet) setPacket(generatedPacket);
        if (generatedImprovement && !improvement) setImprovement(generatedImprovement);
        return deriveResumeFitFromPacket(generatedPacket, generatedImprovement, reviewItem);
      },
      (result) => {
        setFit(result);
        onResumeFitUpdated?.(result);
      },
    );
  }

  function updateDecision(status: JobDecisionStatus) {
    if (!reviewItem.job_id) return;
    void runSection(
      "decision",
      () =>
        decision?.id
          ? updateJobDecision(decision.id, { decision_status: status, priority: "medium" })
          : saveJobDecision(reviewItem.job_id, { decision_status: status, priority: "medium" }),
      (updated) => {
        setDecision(updated);
        onDecisionUpdated?.(updated);
      },
    );
  }

  function watchCompany() {
    if (!reviewItem.job_id) return;
    void runSection(
      "watch",
      () =>
        watchCompanyFromJob(reviewItem.job_id, {
          priority: "medium",
          interest_reason: "Added from Application Action Center after reviewing this job.",
          tags: ["application-action-center"],
          remote_interest: remoteInterest(reviewItem.remote_eligibility),
          junior_friendliness_signal: juniorSignal(reviewItem.title),
        }),
      (updated) => {
        setWatchlistItem(updated);
        onWatchCompanyUpdated?.(updated);
      },
    );
  }

  async function copy(text: string | null | undefined, label: string) {
    if (!text) {
      setCopyMessage(`${label} is unavailable.`);
      return;
    }
    try {
      await navigator.clipboard.writeText(text);
      setCopyMessage(`${label} copied.`);
    } catch {
      setCopyMessage(`Could not copy ${label.toLowerCase()}.`);
    }
  }

  function buildExportMarkdown() {
    return buildApplicationExportMarkdown({
      reviewItem,
      activeResume,
      resumeFitResult: fit,
      applicationPacket: packet,
      resumeImprovement: improvement,
      prepNotes: prep,
      decision,
      watchlistItem,
      nextAction,
    });
  }

  async function copyExportMarkdown() {
    const result = await copyApplicationPackMarkdown(buildExportMarkdown());
    setExportMessage(result.ok ? "Copied application pack Markdown." : result.error ?? "Could not copy Markdown.");
  }

  function downloadExportMarkdown() {
    const result = downloadMarkdownFile(buildApplicationExportFilename(reviewItem), buildExportMarkdown());
    setExportMessage(result.ok ? "Downloaded application pack Markdown." : result.error ?? "Could not download Markdown.");
  }

  async function generateMissingMaterials() {
    if (!reviewItem.job_id) return;
    setLoading((current) => ({ ...current, exportGenerate: true }));
    setExportWarning(null);
    setExportMessage(null);
    const failures: string[] = [];
    let generated = 0;
    try {
      if (!packet) {
        try {
          setPacket(await fetchPacket());
          generated += 1;
        } catch {
          failures.push("application packet");
        }
      }
      if (!improvement) {
        try {
          setImprovement(await fetchImprovement());
          generated += 1;
        } catch {
          failures.push("resume improvements");
        }
      }
      if (!prep) {
        try {
          setPrep(await fetchPrep());
          generated += 1;
        } catch {
          failures.push("prep notes");
        }
      }
      if (failures.length) {
        setExportWarning(`Generated ${generated} material${generated === 1 ? "" : "s"}. Could not generate: ${failures.join(", ")}.`);
      } else {
        setExportMessage(generated ? "Generated missing materials." : "All materials were already available.");
      }
    } finally {
      setLoading((current) => ({ ...current, exportGenerate: false }));
    }
  }

  return (
    <div className="fixed inset-0 z-50 bg-[#101828]/30">
      <div className="absolute right-0 top-0 h-full w-full max-w-4xl overflow-y-auto bg-white p-5 shadow-xl">
        <div className="mb-5 flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <h2 className="text-lg font-semibold text-[#171923]">Application Action Center</h2>
            <p className="mt-1 text-sm text-[#667085]">Prepare, track, and act on this job from one place.</p>
          </div>
          <button type="button" onClick={onClose} className="rounded border border-[#c8ced8] px-3 py-2 text-sm font-medium text-[#344054] hover:bg-[#f8fafc]">
            Close
          </button>
        </div>

        {copyMessage ? <p className="mb-4 rounded border border-[#d9dee8] bg-[#fcfcfd] px-3 py-2 text-sm text-[#344054]">{copyMessage}</p> : null}

        <div className="grid gap-5">
          <Panel title="Job Snapshot">
            <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
              <div>
                <h3 className="text-lg font-semibold text-[#171923]">{reviewItem.title}</h3>
                <p className="mt-1 text-sm text-[#667085]">{reviewItem.company_name ?? "Unknown company"}</p>
                <div className="mt-3 flex flex-wrap gap-2 text-xs text-[#475467]">
                  <Badge>Score {reviewItem.total_score ?? 0}</Badge>
                  <Badge>{formatMatchTier(reviewItem.match_tier ?? "unknown")}</Badge>
                  <Badge>{reviewItem.eligibility_status ?? "unknown"}</Badge>
                  <Badge>{formatRemoteEligibility(reviewItem.remote_eligibility ?? "unknown")}</Badge>
                  {reviewItem.source_name || reviewItem.source_platform ? <Badge>{reviewItem.source_name ?? reviewItem.source_platform}</Badge> : null}
                  {salary ? <Badge>{salary}</Badge> : null}
                </div>
                {reviewItem.eligibility_reason ? <p className="mt-3 text-sm leading-6 text-[#344054]">{reviewItem.eligibility_reason}</p> : null}
              </div>
              <div className="flex shrink-0 flex-wrap gap-2">
                {jobUrl ? <a href={jobUrl} target="_blank" rel="noopener noreferrer" className="rounded border border-[#c8ced8] px-3 py-2 text-sm font-medium text-[#344054] hover:bg-[#f8fafc]">Open Job</a> : null}
                {applyUrl ? <a href={applyUrl} target="_blank" rel="noopener noreferrer" className="rounded border border-[#c8ced8] px-3 py-2 text-sm font-medium text-[#344054] hover:bg-[#f8fafc]">Open Apply Link</a> : null}
                <button type="button" onClick={() => copy(reviewItem.job_url ?? reviewItem.apply_url, "Job URL")} className="rounded border border-[#c8ced8] px-3 py-2 text-sm font-medium text-[#344054] hover:bg-[#f8fafc]">Copy Job URL</button>
                <Link href={`/jobs/${reviewItem.job_id}/workspace`} className="rounded bg-[#172033] px-3 py-2 text-sm font-medium text-white hover:bg-[#0f1728]">Open Full Workspace</Link>
              </div>
            </div>
          </Panel>

          <Panel title="Recommended Next Action">
            <p className="text-base font-semibold text-[#171923]">{nextAction}</p>
          </Panel>

          <Panel title="Export Pack">
            <div className="flex flex-wrap gap-2">
              <SectionButton loading={loading.exportGenerate} onClick={() => void generateMissingMaterials()}>
                Generate Missing Materials
              </SectionButton>
              <button type="button" onClick={() => void copyExportMarkdown()} className="mt-3 rounded border border-[#c8ced8] px-3 py-2 text-sm font-medium text-[#344054] hover:bg-[#f8fafc]">
                Copy Markdown
              </button>
              <button type="button" onClick={downloadExportMarkdown} className="mt-3 rounded border border-[#c8ced8] px-3 py-2 text-sm font-medium text-[#344054] hover:bg-[#f8fafc]">
                Download Markdown
              </button>
              <button type="button" onClick={() => setPreviewOpen(true)} className="mt-3 rounded border border-[#c8ced8] px-3 py-2 text-sm font-medium text-[#344054] hover:bg-[#f8fafc]">
                Preview Markdown
              </button>
            </div>
            {missingMaterials.length ? (
              <p className="mt-3 rounded border border-[#fed7aa] bg-[#fff7ed] px-3 py-2 text-sm text-[#9a3412]">
                Some generated materials are missing: {missingMaterials.join(", ")}. Export will include available sections only.
              </p>
            ) : null}
            {exportWarning ? <p className="mt-3 rounded border border-[#fed7aa] bg-[#fff7ed] px-3 py-2 text-sm text-[#9a3412]">{exportWarning}</p> : null}
            {exportMessage ? <p className="mt-3 rounded border border-[#d9dee8] bg-[#fcfcfd] px-3 py-2 text-sm text-[#344054]">{exportMessage}</p> : null}
          </Panel>

          <Panel title="Resume Fit">
            {fit ? (
              <ResumeFitBlock fit={fit} />
            ) : (
              <p className="text-sm text-[#667085]">Resume fit not analyzed yet.</p>
            )}
            {!activeResume ? <p className="mt-2 text-sm text-[#92400e]">No active resume found. Generic review still works.</p> : null}
            <SectionButton loading={loading.resumeFit} onClick={rankWithResume}>
              Rank this job with resume
            </SectionButton>
            <SectionError error={errors.resumeFit} />
          </Panel>

          <Panel title="Application Packet">
            <SectionButton loading={loading.packet} onClick={generatePacket}>Generate Application Packet</SectionButton>
            <SectionError error={errors.packet} />
            {packet ? <ApplicationPacketPanel packet={packet} /> : <EmptyText>No packet generated yet.</EmptyText>}
          </Panel>

          <Panel title="Resume Improvement">
            <SectionButton loading={loading.improvement} onClick={generateImprovement}>Generate Resume Improvements</SectionButton>
            <SectionError error={errors.improvement} />
            {improvement ? <ResumeImprovementPanel improvement={improvement} /> : <EmptyText>No resume improvements generated yet.</EmptyText>}
          </Panel>

          <Panel title="Prep Notes">
            <SectionButton loading={loading.prep} onClick={generatePrep}>Generate Prep Notes</SectionButton>
            <SectionError error={errors.prep} />
            {prep ? <ApplicationPrepPanel prep={prep} /> : <EmptyText>No prep notes generated yet.</EmptyText>}
          </Panel>

          <Panel title="Decision Controls">
            <div className="mb-3 text-sm text-[#667085]">Current status: {decision?.decision_status ?? decision?.status ?? reviewItem.decision_status ?? "none"}</div>
            <div className="flex flex-wrap gap-2">
              {decisionActions.map(([label, status]) => (
                <button key={status} type="button" disabled={loading.decision} onClick={() => updateDecision(status)} className="rounded border border-[#c8ced8] px-3 py-2 text-sm font-medium text-[#344054] hover:bg-[#f8fafc] disabled:cursor-not-allowed disabled:opacity-60">
                  {label}
                </button>
              ))}
            </div>
            <SectionError error={errors.decision} />
          </Panel>

          <Panel title="Company Watch">
            <div className="mb-3 flex flex-wrap gap-2 text-xs text-[#475467]">
              <Badge>{watchlistItem ? "Watched" : reviewItem.company_watch_status ? "Watched" : "Not watched"}</Badge>
              {watchlistItem?.priority ? <Badge>Priority {watchlistItem.priority}</Badge> : null}
              {watchlistItem?.tags?.length ? <Badge>{watchlistItem.tags.join(", ")}</Badge> : null}
            </div>
            {watchlistItem?.notes ? <p className="mb-3 text-sm text-[#667085]">{watchlistItem.notes}</p> : null}
            <SectionButton loading={loading.watch} onClick={watchCompany}>Watch Company</SectionButton>
            <SectionError error={errors.watch} />
          </Panel>

          <Panel title="Final Actions">
            <div className="flex flex-wrap gap-2">
              <Link href={`/jobs/${reviewItem.job_id}/workspace`} className="rounded bg-[#172033] px-3 py-2 text-sm font-medium text-white hover:bg-[#0f1728]">Open Workspace</Link>
              <Link href="/jobs/pipeline" className="rounded border border-[#c8ced8] px-3 py-2 text-sm font-medium text-[#344054] hover:bg-[#f8fafc]">Open Pipeline</Link>
              <Link href="/companies/watchlist" className="rounded border border-[#c8ced8] px-3 py-2 text-sm font-medium text-[#344054] hover:bg-[#f8fafc]">Open Company Watchlist</Link>
              <Link href="/discovery/control-center#review-queue" className="rounded border border-[#c8ced8] px-3 py-2 text-sm font-medium text-[#344054] hover:bg-[#f8fafc]">Back to Review Queue</Link>
            </div>
          </Panel>
        </div>
      </div>
      {previewOpen ? (
        <div className="fixed inset-0 z-[60] bg-[#101828]/40 p-4">
          <div className="mx-auto flex h-full max-w-5xl flex-col rounded-md bg-white shadow-xl">
            <div className="flex flex-col gap-3 border-b border-[#e4e7ec] p-4 sm:flex-row sm:items-start sm:justify-between">
              <div>
                <h3 className="text-base font-semibold text-[#171923]">Preview Markdown</h3>
                <p className="mt-1 break-all text-sm text-[#667085]">{exportFilename}</p>
              </div>
              <div className="flex flex-wrap gap-2">
                <button type="button" onClick={() => void copyExportMarkdown()} className="rounded border border-[#c8ced8] px-3 py-2 text-sm font-medium text-[#344054] hover:bg-[#f8fafc]">
                  Copy Markdown
                </button>
                <button type="button" onClick={downloadExportMarkdown} className="rounded border border-[#c8ced8] px-3 py-2 text-sm font-medium text-[#344054] hover:bg-[#f8fafc]">
                  Download Markdown
                </button>
                <button type="button" onClick={() => setPreviewOpen(false)} className="rounded bg-[#172033] px-3 py-2 text-sm font-medium text-white hover:bg-[#0f1728]">
                  Close
                </button>
              </div>
            </div>
            <pre className="min-h-0 flex-1 overflow-auto whitespace-pre-wrap bg-[#101828] p-4 text-sm leading-6 text-[#f8fafc]">
              <code>{exportMarkdown}</code>
            </pre>
          </div>
        </div>
      ) : null}
    </div>
  );
}

function Panel({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="rounded-md border border-[#d9dee8] bg-white p-4">
      <h3 className="mb-3 text-sm font-semibold uppercase tracking-normal text-[#667085]">{title}</h3>
      {children}
    </section>
  );
}

function SectionButton({ loading, onClick, children }: { loading?: boolean; onClick: () => void; children: ReactNode }) {
  return (
    <button type="button" disabled={loading} onClick={onClick} className="mt-3 rounded bg-[#172033] px-3 py-2 text-sm font-medium text-white hover:bg-[#0f1728] disabled:cursor-not-allowed disabled:opacity-60">
      {loading ? "Working..." : children}
    </button>
  );
}

function SectionError({ error }: { error?: string | null }) {
  return error ? <p className="mt-3 rounded border border-[#fecaca] bg-[#fff7f7] px-3 py-2 text-sm text-[#991b1b]">{error}</p> : null;
}

function EmptyText({ children }: { children: ReactNode }) {
  return <p className="mt-3 text-sm text-[#667085]">{children}</p>;
}

function Badge({ children }: { children: ReactNode }) {
  return <span className="rounded bg-white px-2 py-1 ring-1 ring-[#e4e7ec]">{children}</span>;
}

function ResumeFitBlock({ fit }: { fit: ResumeFitResult }) {
  return (
    <div className="rounded border border-[#dbeafe] bg-[#eff6ff] p-3">
      <div className="flex flex-wrap gap-2 text-xs text-[#1d4ed8]">
        <Badge>Score {fit.resume_fit_score ?? "unknown"}</Badge>
        <Badge>{labelize(fit.resume_fit_tier)}</Badge>
        <Badge>{labelize(fit.resume_action)}</Badge>
      </div>
      {fit.resume_fit_summary ? <p className="mt-3 text-sm text-[#344054]">{fit.resume_fit_summary}</p> : null}
      <div className="mt-3 grid gap-3 md:grid-cols-2">
        <MiniList title="Strengths" items={fit.resume_strengths} />
        <MiniList title="Gaps" items={fit.resume_gaps} />
      </div>
    </div>
  );
}

function MiniList({ title, items }: { title: string; items: string[] }) {
  return (
    <div>
      <h4 className="text-sm font-semibold text-[#344054]">{title}</h4>
      {items.length ? (
        <ul className="mt-1 list-disc space-y-1 pl-5 text-sm text-[#475467]">
          {items.slice(0, 3).map((item) => <li key={item}>{item}</li>)}
        </ul>
      ) : <p className="mt-1 text-sm text-[#667085]">None listed.</p>}
    </div>
  );
}

function recommendedNextAction(
  item: DailyScoutReviewItem,
  fit?: ResumeFitResult | null,
  decision?: JobApplicationDecisionResponse | null,
) {
  const status = decision?.decision_status ?? decision?.status ?? item.decision_status;
  if (status === "applied" || status === "interviewing") return "Already in progress";
  const action = fit?.resume_action ?? item.resume_action;
  if (action === "apply_now") return "Apply now";
  if (action === "tailor_resume") return "Tailor resume first";
  if (action === "cold_dm_first") return "Prepare cold DM";
  if (action === "skip_for_now") return "Skip for now";
  if (fit?.resume_fit_tier === "strong_fit" && (item.eligibility_status === "eligible" || item.match_tier === "best_match")) return "Apply now";
  if (fit?.resume_fit_tier === "good_fit" && item.eligibility_status === "eligible") return "Tailor resume first";
  if (fit?.resume_fit_tier === "needs_tailoring") return "Tailor resume first";
  if (fit?.resume_fit_tier === "weak_fit" && item.eligibility_status === "uncertain") return "Skip for now";
  if (item.match_tier === "worth_checking") return "Needs review";
  if (item.match_tier === "stretch") return "Prepare cold DM";
  if (item.company_watch_status) return "Watch company first";
  return "Save for later";
}

function remoteInterest(value?: string | null) {
  if (value === "work_from_anywhere" || value === "remote_global_unspecified") return "remote_worldwide";
  if (value === "remote_india_eligible") return "remote_india";
  if (value === "hybrid") return "hybrid_possible";
  return "unknown";
}

function juniorSignal(title?: string | null) {
  return /\b(intern|junior|entry[- ]level|new grad)\b/i.test(title ?? "") ? "moderate" : "unknown";
}

function labelize(value?: string | null) {
  return (value ?? "unknown").replace(/_/g, " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function friendlyError(error: unknown) {
  return error instanceof Error ? error.message : "Request failed. Check the backend and try again.";
}
