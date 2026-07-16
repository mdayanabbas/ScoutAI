"use client";

import Link from "next/link";
import { useMemo, useState } from "react";

import { ApplicationPacketPanel } from "@/components/applications/ApplicationPacketPanel";
import { ApplicationPrepPanel } from "@/components/applications/ApplicationPrepPanel";
import { ResumeGapAnalysis } from "@/components/applications/ResumeGapAnalysis";
import { ResumeImprovementPanel } from "@/components/applications/ResumeImprovementPanel";
import { PageHeader } from "@/components/layout/PageHeader";
import {
  decisionStatusLabel,
} from "@/components/recommendations/RecommendedJobCard";
import {
  formatMatchTier,
  formatRemoteEligibility,
  formatSalary,
  labelize,
  normalizeExternalUrl,
} from "@/components/recommendations/recommendation-format";
import { useJobDecisions, useJobDecisionStatusCounts } from "@/hooks/use-job-decisions";
import {
  generateApplicationPacketForDecision,
  generateApplicationPacketForJob,
} from "@/lib/application-packet-api";
import { generateApplicationPrepForDecision } from "@/lib/application-prep-api";
import {
  generateResumeImprovementForDecision,
  generateResumeImprovementForJob,
} from "@/lib/resume-improvements-api";
import type { ApplicationPacketResponse } from "@/types/application-packet";
import type { ApplicationPrepResponse } from "@/types/application-prep";
import type { JobDecisionListItem, JobDecisionStatus } from "@/types/job-decision";
import type { ResumeImprovementResponse } from "@/types/resume-improvement";

const filters: Array<{ label: string; value: string }> = [
  { label: "All", value: "" },
  { label: "Saved", value: "saved" },
  { label: "Needs Resume", value: "needs_custom_resume" },
  { label: "Needs Cold DM", value: "needs_cold_dm" },
  { label: "Applied", value: "applied" },
  { label: "Interviewing", value: "interviewing" },
  { label: "Skipped", value: "skipped" },
  { label: "Archived", value: "archived" },
];

export default function TrackedJobsPage() {
  const [status, setStatus] = useState("");
  const [prepByDecisionId, setPrepByDecisionId] = useState<Record<string, ApplicationPrepResponse>>({});
  const [prepErrors, setPrepErrors] = useState<Record<string, string>>({});
  const [pendingDecisionId, setPendingDecisionId] = useState<string | null>(null);
  const [packetByDecisionId, setPacketByDecisionId] = useState<Record<string, ApplicationPacketResponse>>({});
  const [packetErrors, setPacketErrors] = useState<Record<string, string>>({});
  const [packetPendingDecisionId, setPacketPendingDecisionId] = useState<string | null>(null);
  const [improvementByDecisionId, setImprovementByDecisionId] = useState<Record<string, ResumeImprovementResponse>>({});
  const [improvementErrors, setImprovementErrors] = useState<Record<string, string>>({});
  const [improvementPendingDecisionId, setImprovementPendingDecisionId] = useState<string | null>(null);
  const decisionsQuery = useJobDecisions({
    limit: 50,
    include_archived: status === "archived",
    decision_status: status || undefined,
  });
  const countsQuery = useJobDecisionStatusCounts();
  const decisions = decisionsQuery.data?.items ?? [];

  async function prepareDecision(decision: JobDecisionListItem) {
    setPendingDecisionId(decision.id);
    setPrepErrors((current) => {
      const next = { ...current };
      delete next[decision.id];
      return next;
    });
    try {
      const prep = await generateApplicationPrepForDecision(decision.id);
      setPrepByDecisionId((current) => ({ ...current, [decision.id]: prep }));
      await decisionsQuery.refetch();
      await countsQuery.refetch();
    } catch (error) {
      setPrepErrors((current) => ({
        ...current,
        [decision.id]:
          error instanceof Error ? error.message : "Could not prepare application notes.",
      }));
    } finally {
      setPendingDecisionId(null);
    }
  }

  async function generatePacket(decision: JobDecisionListItem) {
    setPacketPendingDecisionId(decision.id);
    setPacketErrors((current) => {
      const next = { ...current };
      delete next[decision.id];
      return next;
    });
    try {
      const packet = decision.id
        ? await generateApplicationPacketForDecision(decision.id)
        : await generateApplicationPacketForJob(decision.job_id);
      setPacketByDecisionId((current) => ({ ...current, [decision.id]: packet }));
      await decisionsQuery.refetch();
      await countsQuery.refetch();
    } catch (error) {
      setPacketErrors((current) => ({
        ...current,
        [decision.id]:
          error instanceof Error ? error.message : "Could not generate application packet.",
      }));
    } finally {
      setPacketPendingDecisionId(null);
    }
  }

  async function improveResume(decision: JobDecisionListItem) {
    setImprovementPendingDecisionId(decision.id);
    setImprovementErrors((current) => {
      const next = { ...current };
      delete next[decision.id];
      return next;
    });
    try {
      const improvement = decision.id
        ? await generateResumeImprovementForDecision(decision.id)
        : await generateResumeImprovementForJob(decision.job_id);
      setImprovementByDecisionId((current) => ({
        ...current,
        [decision.id]: improvement,
      }));
      await decisionsQuery.refetch();
      await countsQuery.refetch();
    } catch (error) {
      setImprovementErrors((current) => ({
        ...current,
        [decision.id]:
          error instanceof Error
            ? error.message
            : "Could not generate resume improvement suggestions.",
      }));
    } finally {
      setImprovementPendingDecisionId(null);
    }
  }

  return (
    <>
      <PageHeader
        title="Tracked Jobs"
        description="Saved jobs, application status, prep notes, and next actions."
      />

      <TrackedCountSummary counts={countsQuery.data} />

      <div className="mb-5 flex flex-wrap gap-2">
        {filters.map((item) => (
          <button
            key={item.value || "all"}
            type="button"
            onClick={() => setStatus(item.value)}
            className={[
              "rounded border px-3 py-2 text-sm font-medium",
              status === item.value
                ? "border-[#172033] bg-[#172033] text-white"
                : "border-[#c8ced8] bg-white text-[#344054] hover:bg-[#f8fafc]",
            ].join(" ")}
          >
            {item.label}
          </button>
        ))}
      </div>

      {decisionsQuery.isLoading ? <LoadingState /> : null}

      {decisionsQuery.error ? (
        <div className="rounded-md border border-[#fecaca] bg-[#fff7f7] p-4 text-sm text-[#991b1b]">
          Could not load tracked jobs.
        </div>
      ) : null}

      {!decisionsQuery.isLoading && !decisionsQuery.error && decisions.length === 0 ? (
        <div className="rounded-md border border-dashed border-[#c8ced8] bg-white p-8 text-center">
          <h2 className="text-base font-semibold text-[#171923]">No tracked jobs yet.</h2>
          <p className="mt-2 text-sm text-[#667085]">
            Save a recommended job to start tracking your applications.
          </p>
        </div>
      ) : null}

      {decisions.length > 0 ? (
        <section className="space-y-4">
          {decisions.map((decision) => (
            <TrackedJobCard
              key={decision.id}
              decision={decision}
              prep={prepByDecisionId[decision.id] ?? prepFromDecision(decision)}
              prepPending={pendingDecisionId === decision.id}
              prepError={prepErrors[decision.id]}
              onPrepare={() => prepareDecision(decision)}
              packet={packetByDecisionId[decision.id]}
              packetPending={packetPendingDecisionId === decision.id}
              packetError={packetErrors[decision.id]}
              onGeneratePacket={() => generatePacket(decision)}
              improvement={improvementByDecisionId[decision.id]}
              improvementPending={improvementPendingDecisionId === decision.id}
              improvementError={improvementErrors[decision.id]}
              onImproveResume={() => improveResume(decision)}
            />
          ))}
        </section>
      ) : null}
    </>
  );
}

function TrackedJobCard({
  decision,
  prep,
  prepPending,
  prepError,
  onPrepare,
  packet,
  packetPending,
  packetError,
  onGeneratePacket,
  improvement,
  improvementPending,
  improvementError,
  onImproveResume,
}: {
  decision: JobDecisionListItem;
  prep?: ApplicationPrepResponse | null;
  prepPending: boolean;
  prepError?: string;
  onPrepare: () => void;
  packet?: ApplicationPacketResponse | null;
  packetPending: boolean;
  packetError?: string;
  onGeneratePacket: () => void;
  improvement?: ResumeImprovementResponse | null;
  improvementPending: boolean;
  improvementError?: string;
  onImproveResume: () => void;
}) {
  const applyUrl = normalizeExternalUrl(decision.apply_url) ?? normalizeExternalUrl(decision.job_url);
  const salary = formatSalary({
    salary_min: decision.salary_min,
    salary_max: decision.salary_max,
    salary_currency: decision.salary_currency,
  });

  return (
    <article className="rounded-md border border-[#d9dee8] bg-white p-5 shadow-sm">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <div className="flex flex-wrap gap-2">
            <Badge>{decisionStatusLabel(decision.decision_status ?? decision.status ?? "interested")}</Badge>
            {decision.priority ? <Badge>{labelize(decision.priority)}</Badge> : null}
            {decision.match_tier ? <Badge>{formatMatchTier(decision.match_tier)}</Badge> : null}
          </div>
          <h2 className="mt-3 text-lg font-semibold text-[#171923]">
            {decision.title ?? decision.job_title ?? "Tracked job"}
          </h2>
          <div className="mt-1 flex flex-wrap gap-x-3 gap-y-1 text-sm text-[#667085]">
            <span>{decision.company_name ?? "Unknown company"}</span>
            {decision.remote_eligibility ? (
              <span>{formatRemoteEligibility(decision.remote_eligibility)}</span>
            ) : null}
            {decision.total_score != null ? <span>Score {Math.round(decision.total_score)}</span> : null}
            {salary ? <span>{salary}</span> : null}
          </div>
        </div>
        <div className="flex shrink-0 flex-wrap gap-2 lg:justify-end">
          {applyUrl ? (
            <a
              href={applyUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="rounded bg-[#172033] px-3 py-2 text-sm font-medium text-white"
            >
              Apply / View Job
            </a>
          ) : null}
          <Link
            href={`/jobs/${decision.job_id}/workspace`}
            className="rounded border border-[#c8ced8] bg-white px-3 py-2 text-sm font-medium text-[#344054] hover:bg-[#f8fafc]"
          >
            Open Workspace
          </Link>
          <button
            type="button"
            onClick={onPrepare}
            disabled={prepPending}
            className="rounded border border-[#175cd3] bg-white px-3 py-2 text-sm font-medium text-[#175cd3] hover:bg-[#eff6ff] disabled:cursor-not-allowed disabled:opacity-60"
          >
            {prepPending ? "Preparing..." : prep ? "Regenerate Prep" : "Prepare Application"}
          </button>
          <button
            type="button"
            onClick={onGeneratePacket}
            disabled={packetPending}
            className="rounded border border-[#166534] bg-white px-3 py-2 text-sm font-medium text-[#166534] hover:bg-[#f0fdf4] disabled:cursor-not-allowed disabled:opacity-60"
          >
            {packetPending
              ? "Generating packet..."
              : packet
                ? "Regenerate Packet"
                : "Generate Packet"}
          </button>
          <button
            type="button"
            onClick={onImproveResume}
            disabled={improvementPending}
            className="rounded border border-[#7c3aed] bg-white px-3 py-2 text-sm font-medium text-[#6d28d9] hover:bg-[#f5f3ff] disabled:cursor-not-allowed disabled:opacity-60"
          >
            {improvementPending
              ? "Generating resume suggestions..."
              : improvement
                ? "Regenerate Resume Suggestions"
                : "Improve Resume"}
          </button>
        </div>
      </div>

      {decision.next_action ? (
        <p className="mt-4 rounded border border-[#d9dee8] bg-[#f8fafc] px-3 py-2 text-sm text-[#344054]">
          <span className="font-medium">Next action:</span> {decision.next_action}
        </p>
      ) : null}

      {decision.notes ? (
        <p className="mt-3 rounded border border-[#edf0f5] bg-[#fcfcfd] px-3 py-2 text-sm text-[#344054]">
          <span className="font-medium">Notes:</span> {decision.notes}
        </p>
      ) : null}

      {prepError ? (
        <div className="mt-4 rounded border border-[#fecaca] bg-[#fff7f7] p-3 text-sm text-[#991b1b]">
          Could not prepare application notes.
        </div>
      ) : null}

      {prep ? <ApplicationPrepPanel prep={prep} compact={!prepByDecisionHasDetails(prep)} /> : null}

      {!packet && !packetPending && !packetError ? (
        <p className="mt-4 rounded border border-[#edf0f5] bg-[#fcfcfd] px-3 py-2 text-sm text-[#667085]">
          Generate packet to compare this job with your resume.
        </p>
      ) : null}

      {packetError ? (
        <div className="mt-4 rounded border border-[#fecaca] bg-[#fff7f7] p-3 text-sm text-[#991b1b]">
          <div className="font-medium">Could not generate application packet.</div>
          <p className="mt-1">{packetError}</p>
          <button
            type="button"
            onClick={onGeneratePacket}
            className="mt-3 rounded bg-[#172033] px-3 py-2 text-sm font-medium text-white"
          >
            Retry
          </button>
        </div>
      ) : null}

      {packet?.resume_used ? (
        <div className="mt-4">
          <ResumeGapAnalysis
            resumeUsed={packet.resume_used}
            resumeMatchSummary={packet.resume_match_summary}
            resumeStrengths={packet.resume_strengths}
            resumeGaps={packet.resume_gaps}
            resumeBulletSources={packet.resume_bullet_sources}
            compact
          />
        </div>
      ) : null}

      {packet ? <ApplicationPacketPanel packet={packet} /> : null}

      {improvementError ? (
        <div className="mt-4 rounded border border-[#fecaca] bg-[#fff7f7] p-3 text-sm text-[#991b1b]">
          <div className="font-medium">Could not generate resume improvement suggestions.</div>
          <p className="mt-1">{improvementError}</p>
          <button
            type="button"
            onClick={onImproveResume}
            className="mt-3 rounded bg-[#172033] px-3 py-2 text-sm font-medium text-white"
          >
            Retry
          </button>
        </div>
      ) : null}

      {improvement ? <ResumeImprovementPanel improvement={improvement} /> : null}
    </article>
  );
}

function prepFromDecision(decision: JobDecisionListItem): ApplicationPrepResponse | null {
  if (!decision.fit_summary && !decision.next_action) {
    return null;
  }
  return {
    job_id: decision.job_id,
    decision_id: decision.id,
    title: decision.title ?? decision.job_title,
    company_name: decision.company_name,
    match_tier: decision.match_tier,
    total_score: decision.total_score,
    remote_eligibility: decision.remote_eligibility,
    fit_summary: decision.fit_summary,
    concerns: normalizeConcerns(decision.concerns),
    suggested_next_action: decision.next_action,
    resume_focus_points: [],
    project_talking_points: [],
    application_checklist: [],
    missing_information: [],
  };
}

function normalizeConcerns(value: unknown) {
  if (Array.isArray(value)) {
    return value.map((item) => ({ label: "Concern", value: String(item), reason: "Stored prep concern." }));
  }
  if (typeof value === "string" && value.trim()) {
    return value.split("\n").map((item) => ({ label: "Concern", value: item, reason: "Stored prep concern." }));
  }
  return [];
}

function prepByDecisionHasDetails(prep: ApplicationPrepResponse) {
  return Boolean(
    (prep.resume_focus_points ?? []).length ||
      (prep.project_talking_points ?? []).length ||
      (prep.application_checklist ?? []).length ||
      prep.cold_dm_angle,
  );
}

function TrackedCountSummary({ counts }: { counts?: Record<string, number | undefined> }) {
  const cards = useMemo(
    () => [
      ["Saved", counts?.saved ?? 0],
      ["Needs Resume", counts?.needs_custom_resume ?? 0],
      ["Needs Cold DM", counts?.needs_cold_dm ?? 0],
      ["Applied", counts?.applied ?? 0],
      ["Interviewing", counts?.interviewing ?? 0],
    ],
    [counts],
  );
  return (
    <section className="mb-5 grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
      {cards.map(([label, value]) => (
        <div key={label} className="rounded-md border border-[#d9dee8] bg-white p-4">
          <div className="text-xs font-medium uppercase tracking-normal text-[#667085]">
            {label}
          </div>
          <div className="mt-2 text-2xl font-semibold text-[#171923]">{value}</div>
        </div>
      ))}
    </section>
  );
}

function Badge({ children }: { children: string }) {
  return (
    <span className="rounded-full border border-[#d9dee8] bg-[#f8fafc] px-2 py-0.5 text-xs font-medium text-[#475467]">
      {children}
    </span>
  );
}

function LoadingState() {
  return (
    <div className="space-y-4">
      {Array.from({ length: 3 }).map((_, index) => (
        <div
          key={index}
          className="h-40 animate-pulse rounded-md border border-[#d9dee8] bg-white"
        />
      ))}
    </div>
  );
}
