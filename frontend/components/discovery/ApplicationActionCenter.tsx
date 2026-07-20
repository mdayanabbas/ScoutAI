"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
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
import {
  applicationFollowUpStorage,
  outreachTypeFromDraftTarget,
  type ApplicationFollowUpItem,
} from "@/lib/application-follow-ups";
import {
  buildColdDmDraft,
  coldDmLengthOptions,
  coldDmTargetOptions,
  coldDmToneOptions,
  copyColdDmDraft,
  defaultColdDmLength,
  deleteSavedColdDmDraft,
  generateColdDmVariants,
  saveColdDmDraft,
  savedDraftsForJob,
  type ColdDmDraftResult,
  type ColdDmLength,
  type ColdDmTargetType,
  type ColdDmTone,
  type SavedColdDmDraft,
} from "@/lib/cold-dm-draft";
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
  initialSection,
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
  initialSection?: "cold_dm" | "export";
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
  const [coldDmTarget, setColdDmTarget] = useState<ColdDmTargetType>("founder");
  const [coldDmTone, setColdDmTone] = useState<ColdDmTone>("confident");
  const [coldDmLength, setColdDmLength] = useState<ColdDmLength>("medium");
  const [includeProjects, setIncludeProjects] = useState(true);
  const [includeResumeFit, setIncludeResumeFit] = useState(true);
  const [includeRemoteFit, setIncludeRemoteFit] = useState(true);
  const [includeAsk, setIncludeAsk] = useState(true);
  const [includeColdDmOutline, setIncludeColdDmOutline] = useState(true);
  const [recipientName, setRecipientName] = useState("");
  const [companyContext, setCompanyContext] = useState("");
  const [customProofPoint, setCustomProofPoint] = useState("");
  const [customAsk, setCustomAsk] = useState("");
  const [coldDmDrafts, setColdDmDrafts] = useState<ColdDmDraftResult[]>([]);
  const [selectedColdDmDraftId, setSelectedColdDmDraftId] = useState<string | null>(null);
  const [savedDrafts, setSavedDrafts] = useState<SavedColdDmDraft[]>([]);
  const [coldDmMessage, setColdDmMessage] = useState<string | null>(null);
  const [coldDmError, setColdDmError] = useState<string | null>(null);
  const [followUps, setFollowUps] = useState<ApplicationFollowUpItem[]>([]);
  const [followUpDueDate, setFollowUpDueDate] = useState("");
  const [followUpMessage, setFollowUpMessage] = useState<string | null>(null);
  const [followUpError, setFollowUpError] = useState<string | null>(null);

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
  const selectedColdDmDraft = coldDmDrafts.find((draft) => draft.id === selectedColdDmDraftId) ?? coldDmDrafts[0] ?? null;

  useEffect(() => {
    setSavedDrafts(savedDraftsForJob(reviewItem.job_id));
    setFollowUps(applicationFollowUpStorage.getFollowUpsForJob(reviewItem.job_id));
  }, [reviewItem.job_id]);

  useEffect(() => {
    if (initialSection === "cold_dm") {
      window.setTimeout(() => document.getElementById("cold-dm-builder")?.scrollIntoView({ block: "start", behavior: "smooth" }), 0);
    }
    if (initialSection === "export") {
      window.setTimeout(() => document.getElementById("export-pack")?.scrollIntoView({ block: "start", behavior: "smooth" }), 0);
    }
  }, [initialSection]);

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
      coldDmDrafts: [...coldDmDrafts, ...savedDrafts],
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

  function coldDmInput(tone = coldDmTone) {
    return {
      reviewItem,
      activeResume,
      resumeFitResult: fit,
      applicationPacket: packet,
      resumeImprovement: improvement,
      prepNotes: prep,
      decision,
      watchlistItem,
      targetType: coldDmTarget,
      tone,
      length: coldDmLength,
      includeProjects,
      includeResumeFit,
      includeRemoteFit,
      includeAsk,
      includeColdDmOutline,
      customRecipientName: recipientName,
      customCompanyContext: companyContext,
      customProofPoint,
      customAsk,
    };
  }

  function generateColdDmDraft() {
    setColdDmError(null);
    const draft = buildColdDmDraft(coldDmInput());
    setColdDmDrafts([draft]);
    setSelectedColdDmDraftId(draft.id);
    setColdDmMessage("Generated cold DM draft.");
  }

  function regenerateColdDmDraft() {
    generateColdDmDraft();
  }

  function generateColdDmVariantDrafts() {
    setColdDmError(null);
    const variants = generateColdDmVariants(coldDmInput());
    setColdDmDrafts(variants);
    setSelectedColdDmDraftId(variants[0]?.id ?? null);
    setColdDmMessage("Generated three draft variants.");
  }

  async function copyDraft(draft: ColdDmDraftResult | SavedColdDmDraft) {
    const result = await copyColdDmDraft(draft.body);
    setColdDmMessage(result.ok ? "Copied cold DM draft." : result.error ?? "Could not copy draft.");
    if (result.ok) setColdDmError(null);
  }

  function saveDraft(draft: ColdDmDraftResult) {
    const result = saveColdDmDraft(draft, reviewItem);
    if (!result.ok) {
      setColdDmError(result.error ?? "Could not save draft locally.");
      return;
    }
    setSavedDrafts(savedDraftsForJob(reviewItem.job_id));
    setColdDmMessage("Saved draft locally.");
    setColdDmError(null);
  }

  function deleteDraft(draftId: string) {
    const result = deleteSavedColdDmDraft(draftId);
    if (!result.ok) {
      setColdDmError(result.error ?? "Could not delete draft.");
      return;
    }
    setSavedDrafts(savedDraftsForJob(reviewItem.job_id));
    setColdDmMessage("Deleted saved draft.");
  }

  function refreshFollowUps(note?: string) {
    setFollowUps(applicationFollowUpStorage.getFollowUpsForJob(reviewItem.job_id));
    if (note) setFollowUpMessage(note);
  }

  function trackDraft(status: "drafted" | "copied", draft: ColdDmDraftResult | SavedColdDmDraft | null = selectedColdDmDraft) {
    if (!draft) {
      setFollowUpError("Generate or select a draft first.");
      return;
    }
    const result = status === "drafted"
      ? applicationFollowUpStorage.markDrafted(reviewItem.job_id, { draft, message_target: recipientName || null }, reviewItem)
      : applicationFollowUpStorage.markCopied(reviewItem.job_id, { draft, message_target: recipientName || null }, reviewItem);
    if (!result.ok) {
      setFollowUpError(result.error ?? "Could not track follow-up.");
      return;
    }
    setFollowUpError(null);
    refreshFollowUps(status === "drafted" ? "Tracked draft." : "Tracked copied draft.");
  }

  function markOutreachSent() {
    const due = followUpDueDate ? new Date(followUpDueDate).toISOString() : undefined;
    const result = applicationFollowUpStorage.markSentManually(reviewItem.job_id, new Date().toISOString(), due);
    if (!result.ok) {
      setFollowUpError(result.error ?? "Could not mark outreach sent.");
      return;
    }
    setFollowUpError(null);
    refreshFollowUps("Marked outreach as manually sent.");
  }

  function updateFollowUp(id: string, changes: Partial<ApplicationFollowUpItem>, note: string) {
    const result = applicationFollowUpStorage.updateFollowUp(id, changes);
    if (!result.ok) {
      setFollowUpError(result.error ?? "Could not update follow-up.");
      return;
    }
    setFollowUpError(null);
    refreshFollowUps(note);
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

          <section id="export-pack">
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
          </section>

          <section id="cold-dm-builder">
            <Panel title="Cold DM Draft Builder">
              <p className="text-sm text-[#667085]">Create outreach drafts from the job, resume fit, and application materials.</p>
              <div className="mt-4 grid gap-3 md:grid-cols-3">
                <label className="text-sm font-medium text-[#344054]">
                  Target
                  <select
                    value={coldDmTarget}
                    onChange={(event) => {
                      const value = event.target.value as ColdDmTargetType;
                      setColdDmTarget(value);
                      setColdDmLength(defaultColdDmLength(value));
                    }}
                    className="mt-1 w-full rounded border border-[#c8ced8] px-3 py-2 text-sm"
                  >
                    {coldDmTargetOptions.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
                  </select>
                </label>
                <label className="text-sm font-medium text-[#344054]">
                  Tone
                  <select value={coldDmTone} onChange={(event) => setColdDmTone(event.target.value as ColdDmTone)} className="mt-1 w-full rounded border border-[#c8ced8] px-3 py-2 text-sm">
                    {coldDmToneOptions.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
                  </select>
                </label>
                <label className="text-sm font-medium text-[#344054]">
                  Length
                  <select value={coldDmLength} onChange={(event) => setColdDmLength(event.target.value as ColdDmLength)} className="mt-1 w-full rounded border border-[#c8ced8] px-3 py-2 text-sm">
                    {coldDmLengthOptions.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
                  </select>
                </label>
              </div>
              <div className="mt-3 grid gap-3 md:grid-cols-2">
                <label className="text-sm font-medium text-[#344054]">
                  Recipient name
                  <input value={recipientName} onChange={(event) => setRecipientName(event.target.value)} placeholder="Optional" className="mt-1 w-full rounded border border-[#c8ced8] px-3 py-2 text-sm" />
                </label>
                <label className="text-sm font-medium text-[#344054]">
                  Custom ask
                  <input value={customAsk} onChange={(event) => setCustomAsk(event.target.value)} placeholder="Would you be open to..." className="mt-1 w-full rounded border border-[#c8ced8] px-3 py-2 text-sm" />
                </label>
                <label className="text-sm font-medium text-[#344054] md:col-span-2">
                  Company context
                  <textarea value={companyContext} onChange={(event) => setCompanyContext(event.target.value)} rows={2} placeholder="Optional context you know is true." className="mt-1 w-full rounded border border-[#c8ced8] px-3 py-2 text-sm" />
                </label>
                <label className="text-sm font-medium text-[#344054] md:col-span-2">
                  Custom proof point
                  <textarea value={customProofPoint} onChange={(event) => setCustomProofPoint(event.target.value)} rows={2} placeholder="Optional project or resume proof point." className="mt-1 w-full rounded border border-[#c8ced8] px-3 py-2 text-sm" />
                </label>
              </div>
              <div className="mt-3 flex flex-wrap gap-3 text-sm text-[#344054]">
                <Toggle checked={includeResumeFit} onChange={setIncludeResumeFit} label="Include resume fit" />
                <Toggle checked={includeProjects} onChange={setIncludeProjects} label="Include project evidence" />
                <Toggle checked={includeRemoteFit} onChange={setIncludeRemoteFit} label="Include remote fit" />
                <Toggle checked={includeColdDmOutline} onChange={setIncludeColdDmOutline} label="Include packet cold DM outline" />
                <Toggle checked={includeAsk} onChange={setIncludeAsk} label="Include direct ask" />
              </div>
              <div className="mt-4 flex flex-wrap gap-2">
                <button type="button" onClick={generateColdDmDraft} className="rounded bg-[#172033] px-3 py-2 text-sm font-medium text-white hover:bg-[#0f1728]">
                  Generate Draft
                </button>
                <button type="button" onClick={generateColdDmVariantDrafts} className="rounded border border-[#c8ced8] px-3 py-2 text-sm font-medium text-[#344054] hover:bg-[#f8fafc]">
                  Generate Variants
                </button>
                {selectedColdDmDraft ? (
                  <button type="button" onClick={() => updateDecision("needs_cold_dm")} className="rounded border border-[#c8ced8] px-3 py-2 text-sm font-medium text-[#344054] hover:bg-[#f8fafc]">
                    Mark Needs Cold DM
                  </button>
                ) : null}
              </div>
              {coldDmMessage ? <p className="mt-3 rounded border border-[#d9dee8] bg-[#fcfcfd] px-3 py-2 text-sm text-[#344054]">{coldDmMessage}</p> : null}
              {coldDmError ? <p className="mt-3 rounded border border-[#fecaca] bg-[#fff7f7] px-3 py-2 text-sm text-[#991b1b]">{coldDmError}</p> : null}
              <div className="mt-4 grid gap-3">
                {coldDmDrafts.map((draft) => (
                  <ColdDmDraftCard
                    key={draft.id}
                    draft={draft}
                    selected={draft.id === selectedColdDmDraftId}
                    onSelect={() => setSelectedColdDmDraftId(draft.id)}
                    onCopy={() => void copyDraft(draft)}
                    onRegenerate={regenerateColdDmDraft}
                    onSave={() => saveDraft(draft)}
                    onTrackDrafted={() => trackDraft("drafted", draft)}
                    onTrackCopied={() => trackDraft("copied", draft)}
                    onMarkSent={markOutreachSent}
                    onExport={() => {
                      setSelectedColdDmDraftId(draft.id);
                      document.getElementById("export-pack")?.scrollIntoView({ block: "start", behavior: "smooth" });
                    }}
                  />
                ))}
              </div>
              <details className="mt-4">
                <summary className="cursor-pointer text-sm font-medium text-[#175cd3]">View Saved Drafts for this Job ({savedDrafts.length})</summary>
                <div className="mt-3 grid gap-3">
                  {savedDrafts.length ? savedDrafts.map((draft) => (
                    <SavedDraftCard
                      key={draft.id}
                      draft={draft}
                      onCopy={() => void copyDraft(draft)}
                      onDelete={() => deleteDraft(draft.id)}
                    />
                  )) : <p className="text-sm text-[#667085]">No saved drafts for this job yet.</p>}
                </div>
              </details>
            </Panel>
          </section>

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

          <Panel title="Follow-up Tracking">
            {followUps.length ? (
              <div className="grid gap-3">
                {followUps.map((item) => (
                  <div key={item.id} className="rounded border border-[#e4e7ec] bg-[#fcfcfd] p-3">
                    <div className="flex flex-wrap gap-2 text-xs text-[#475467]">
                      <Badge>{labelize(item.outreach_type)}</Badge>
                      <Badge>{labelize(item.outreach_status)}</Badge>
                      {item.follow_up_due_at ? <Badge>Due {formatShortDate(item.follow_up_due_at)}</Badge> : null}
                    </div>
                    {item.draft_preview ? <p className="mt-2 text-sm text-[#344054]">{item.draft_preview}</p> : null}
                    {item.notes ? <p className="mt-2 text-sm text-[#667085]">{item.notes}</p> : null}
                    <div className="mt-3 flex flex-wrap gap-2">
                      <button type="button" onClick={() => updateFollowUp(item.id, { outreach_status: "follow_up_sent", follow_up_sent_at: new Date().toISOString() }, "Marked follow-up sent.")} className="rounded border border-[#c8ced8] px-2.5 py-1.5 text-xs font-medium text-[#344054] hover:bg-white">Mark Follow-up Sent</button>
                      <button type="button" onClick={() => updateFollowUp(item.id, { outreach_status: "responded" }, "Marked responded.")} className="rounded border border-[#c8ced8] px-2.5 py-1.5 text-xs font-medium text-[#344054] hover:bg-white">Mark Responded</button>
                      <button type="button" onClick={() => updateFollowUp(item.id, { outreach_status: "closed" }, "Closed follow-up.")} className="rounded border border-[#c8ced8] px-2.5 py-1.5 text-xs font-medium text-[#344054] hover:bg-white">Close Follow-up</button>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-[#667085]">Not tracked yet.</p>
            )}
            <div className="mt-4 grid gap-3 sm:grid-cols-[1fr_auto] sm:items-end">
              <label className="text-sm font-medium text-[#344054]">
                Follow-up date
                <input type="datetime-local" value={followUpDueDate} onChange={(event) => setFollowUpDueDate(event.target.value)} className="mt-1 w-full rounded border border-[#c8ced8] px-3 py-2 text-sm" />
              </label>
              <button type="button" onClick={markOutreachSent} className="rounded bg-[#172033] px-3 py-2 text-sm font-medium text-white hover:bg-[#0f1728]">
                Mark Sent Manually
              </button>
            </div>
            <div className="mt-3 flex flex-wrap gap-2">
              <button type="button" onClick={() => trackDraft("drafted")} className="rounded border border-[#c8ced8] px-3 py-2 text-sm font-medium text-[#344054] hover:bg-[#f8fafc]">Track Draft</button>
              <button type="button" onClick={() => trackDraft("copied")} className="rounded border border-[#c8ced8] px-3 py-2 text-sm font-medium text-[#344054] hover:bg-[#f8fafc]">Mark Copied</button>
              <button type="button" onClick={() => updateDecision("interested")} className="rounded border border-[#c8ced8] px-3 py-2 text-sm font-medium text-[#344054] hover:bg-[#f8fafc]">Mark Interested</button>
              <button type="button" onClick={() => updateDecision("needs_cold_dm")} className="rounded border border-[#c8ced8] px-3 py-2 text-sm font-medium text-[#344054] hover:bg-[#f8fafc]">Mark Needs Cold DM</button>
              <button type="button" onClick={() => updateDecision("applied")} className="rounded border border-[#c8ced8] px-3 py-2 text-sm font-medium text-[#344054] hover:bg-[#f8fafc]">Mark Applied</button>
              <Link href="/applications/follow-ups" className="rounded border border-[#c8ced8] px-3 py-2 text-sm font-medium text-[#344054] hover:bg-[#f8fafc]">Open Follow-up Tracker</Link>
            </div>
            <p className="mt-3 text-sm text-[#667085]">ScoutAI only tracks manual outreach here. It will not send or schedule messages.</p>
            {followUpMessage ? <p className="mt-3 rounded border border-[#d9dee8] bg-[#fcfcfd] px-3 py-2 text-sm text-[#344054]">{followUpMessage}</p> : null}
            {followUpError ? <p className="mt-3 rounded border border-[#fecaca] bg-[#fff7f7] px-3 py-2 text-sm text-[#991b1b]">{followUpError}</p> : null}
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
              <Link href="/applications/command-center" className="rounded border border-[#c8ced8] px-3 py-2 text-sm font-medium text-[#344054] hover:bg-[#f8fafc]">Open Command Center</Link>
              <Link href="/jobs/pipeline" className="rounded border border-[#c8ced8] px-3 py-2 text-sm font-medium text-[#344054] hover:bg-[#f8fafc]">Open Pipeline</Link>
              <Link href="/applications/follow-ups" className="rounded border border-[#c8ced8] px-3 py-2 text-sm font-medium text-[#344054] hover:bg-[#f8fafc]">Open Follow-up Tracker</Link>
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

function Toggle({ checked, onChange, label }: { checked: boolean; onChange: (value: boolean) => void; label: string }) {
  return (
    <label className="flex items-center gap-2">
      <input type="checkbox" checked={checked} onChange={(event) => onChange(event.target.checked)} className="h-4 w-4 accent-[#172033]" />
      {label}
    </label>
  );
}

function ColdDmDraftCard({
  draft,
  selected,
  onSelect,
  onCopy,
  onRegenerate,
  onSave,
  onTrackDrafted,
  onTrackCopied,
  onMarkSent,
  onExport,
}: {
  draft: ColdDmDraftResult;
  selected: boolean;
  onSelect: () => void;
  onCopy: () => void;
  onRegenerate: () => void;
  onSave: () => void;
  onTrackDrafted: () => void;
  onTrackCopied: () => void;
  onMarkSent: () => void;
  onExport: () => void;
}) {
  return (
    <article className={`rounded border p-3 ${selected ? "border-[#93c5fd] bg-[#eff6ff]" : "border-[#e4e7ec] bg-[#fcfcfd]"}`}>
      <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h4 className="text-sm font-semibold text-[#171923]">{draft.title}</h4>
          <p className="mt-1 text-xs text-[#667085]">{draft.wordCount} words / {draft.characterCount} characters</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <button type="button" onClick={onSelect} className="rounded border border-[#c8ced8] px-2.5 py-1.5 text-xs font-medium text-[#344054] hover:bg-white">
            Select
          </button>
          <button type="button" onClick={onCopy} className="rounded border border-[#c8ced8] px-2.5 py-1.5 text-xs font-medium text-[#344054] hover:bg-white">
            Copy Draft
          </button>
          <button type="button" onClick={onRegenerate} className="rounded border border-[#c8ced8] px-2.5 py-1.5 text-xs font-medium text-[#344054] hover:bg-white">
            Regenerate
          </button>
          <button type="button" onClick={onSave} className="rounded bg-[#172033] px-2.5 py-1.5 text-xs font-medium text-white hover:bg-[#0f1728]">
            Save Draft Locally
          </button>
          <button type="button" onClick={onTrackDrafted} className="rounded border border-[#c8ced8] px-2.5 py-1.5 text-xs font-medium text-[#344054] hover:bg-white">
            Track as Drafted
          </button>
          <button type="button" onClick={onTrackCopied} className="rounded border border-[#c8ced8] px-2.5 py-1.5 text-xs font-medium text-[#344054] hover:bg-white">
            Track as Copied
          </button>
          <button type="button" onClick={onMarkSent} className="rounded border border-[#c8ced8] px-2.5 py-1.5 text-xs font-medium text-[#344054] hover:bg-white">
            Mark as Manually Sent
          </button>
          <button type="button" onClick={onExport} className="rounded border border-[#c8ced8] px-2.5 py-1.5 text-xs font-medium text-[#344054] hover:bg-white">
            Export with Application Pack
          </button>
        </div>
      </div>
      {draft.subjectLine ? <p className="mt-3 text-sm font-medium text-[#344054]">Subject: {draft.subjectLine}</p> : null}
      <pre className="mt-3 whitespace-pre-wrap rounded bg-white p-3 text-sm leading-6 text-[#344054] ring-1 ring-[#e4e7ec]">{draft.body}</pre>
      {draft.warnings.length ? (
        <ul className="mt-3 list-disc space-y-1 pl-5 text-sm text-[#9a3412]">
          {draft.warnings.map((warning) => <li key={warning}>{warning}</li>)}
        </ul>
      ) : null}
    </article>
  );
}

function SavedDraftCard({
  draft,
  onCopy,
  onDelete,
}: {
  draft: SavedColdDmDraft;
  onCopy: () => void;
  onDelete: () => void;
}) {
  return (
    <article className="rounded border border-[#e4e7ec] bg-[#fcfcfd] p-3">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h4 className="text-sm font-semibold text-[#171923]">{draft.title ?? "Saved cold DM draft"}</h4>
          <p className="mt-1 text-xs text-[#667085]">{labelize(draft.targetType)} / {labelize(draft.tone)} / saved {formatShortDate(draft.generatedAt)}</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <button type="button" onClick={onCopy} className="rounded border border-[#c8ced8] px-2.5 py-1.5 text-xs font-medium text-[#344054] hover:bg-white">
            Copy
          </button>
          <button type="button" onClick={onDelete} className="rounded border border-[#fecaca] px-2.5 py-1.5 text-xs font-medium text-[#991b1b] hover:bg-[#fff7f7]">
            Delete
          </button>
        </div>
      </div>
      <pre className="mt-3 whitespace-pre-wrap rounded bg-white p-3 text-sm leading-6 text-[#344054] ring-1 ring-[#e4e7ec]">{draft.body}</pre>
    </article>
  );
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

function formatShortDate(value?: string | null) {
  if (!value) return "unknown";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleDateString();
}

function friendlyError(error: unknown) {
  return error instanceof Error ? error.message : "Request failed. Check the backend and try again.";
}
