"use client";

import Link from "next/link";

import { WatchCompanyButton } from "@/components/companies/WatchCompanyButton";
import { ApplicationPacketPanel } from "@/components/applications/ApplicationPacketPanel";
import { ApplicationPrepPanel } from "@/components/applications/ApplicationPrepPanel";
import { ResumeImprovementPanel } from "@/components/applications/ResumeImprovementPanel";
import {
  applyUrlForJob,
  formatEligibility,
  formatExperience,
  formatMatchTier,
  formatRemoteEligibility,
  formatSalary,
  labelize,
  sourceAttribution,
} from "@/components/recommendations/recommendation-format";
import type {
  JobApplicationDecisionResponse,
  JobDecisionPayload,
  JobDecisionPriority,
  JobDecisionStatus,
} from "@/types/job-decision";
import type { ApplicationPrepResponse } from "@/types/application-prep";
import type { ApplicationPacketResponse } from "@/types/application-packet";
import type { ResumeImprovementResponse } from "@/types/resume-improvement";
import type { RecommendedJobMatch } from "@/types/job-match";
import { useEffect, useState } from "react";

export function RecommendedJobCard({
  job,
  decision,
  decisionPending = false,
  onDecisionAction,
  onDecisionUpdate,
  prep,
  prepPending = false,
  prepError,
  onPrepareApplication,
  packet,
  packetPending = false,
  packetError,
  onGeneratePacket,
  activeResumeParsed = false,
  improvement,
  improvementPending = false,
  improvementError,
  onImproveResume,
}: {
  job: RecommendedJobMatch;
  decision?: JobApplicationDecisionResponse | null;
  decisionPending?: boolean;
  onDecisionAction?: (job: RecommendedJobMatch, payload: JobDecisionPayload) => void;
  onDecisionUpdate?: (
    decision: JobApplicationDecisionResponse,
    payload: JobDecisionPayload,
  ) => void;
  prep?: ApplicationPrepResponse | null;
  prepPending?: boolean;
  prepError?: string | null;
  onPrepareApplication?: (job: RecommendedJobMatch) => void;
  packet?: ApplicationPacketResponse | null;
  packetPending?: boolean;
  packetError?: string | null;
  onGeneratePacket?: (job: RecommendedJobMatch) => void;
  activeResumeParsed?: boolean;
  improvement?: ResumeImprovementResponse | null;
  improvementPending?: boolean;
  improvementError?: string | null;
  onImproveResume?: (job: RecommendedJobMatch) => void;
}) {
  const salary = formatSalary(job);
  const applyUrl = applyUrlForJob(job);
  const attribution = sourceAttribution(job.job_url);
  const unsuitable = job.eligibility_status === "unsuitable";
  const remoteUnverified =
    job.remote_eligibility === "unknown" ||
    job.remote_eligibility === "remote_eligibility_unclear";
  const [applyViewed, setApplyViewed] = useState(false);
  const [notes, setNotes] = useState(decision?.notes ?? "");
  const [nextAction, setNextAction] = useState(decision?.next_action ?? "");
  const [priority, setPriority] = useState<JobDecisionPriority>(
    decision?.priority ?? "medium",
  );

  useEffect(() => {
    setNotes(decision?.notes ?? "");
    setNextAction(decision?.next_action ?? "");
    setPriority(decision?.priority ?? "medium");
  }, [decision?.id, decision?.notes, decision?.next_action, decision?.priority]);

  return (
    <article
      className={[
        "rounded-md border bg-white p-5 shadow-sm",
        unsuitable ? "border-[#fecaca]" : "border-[#d9dee8]",
      ].join(" ")}
    >
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <Badge tone={tierTone(job.match_tier)}>
              {formatMatchTier(job.match_tier)}
            </Badge>
            <Badge tone={eligibilityTone(job.eligibility_status)}>
              {formatEligibility(job.eligibility_status)}
            </Badge>
            {job.is_stale ? <Badge tone="warning">Score may be stale</Badge> : null}
            {remoteUnverified ? (
              <Badge tone="warning">Remote status unverified</Badge>
            ) : null}
            {decision?.decision_status ? (
              <Badge tone={decisionTone(decision.decision_status)}>
                {decisionStatusLabel(decision.decision_status)}
              </Badge>
            ) : null}
          </div>

          <h2 className="mt-3 text-lg font-semibold tracking-normal text-[#171923]">
            {job.title}
          </h2>
          <div className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-sm text-[#667085]">
            <Link
              href={`/companies/${job.company_id}`}
              className="font-medium text-[#175cd3] hover:underline"
            >
              {job.company_name ?? "Unknown company"}
            </Link>
            <span>{labelize(job.role_category)}</span>
            <span>{job.location ?? "Location not specified"}</span>
          </div>
        </div>

        <div className="flex shrink-0 flex-col items-start gap-2 sm:flex-row lg:flex-col lg:items-end">
          <div className="rounded border border-[#d9dee8] bg-[#f8fafc] px-3 py-2 text-right">
            <div className="text-xs uppercase tracking-normal text-[#667085]">
              Score
            </div>
            <div className="text-xl font-semibold text-[#171923]">
              {Math.round(job.total_score)}
            </div>
          </div>
          {applyUrl ? (
            <a
              href={applyUrl}
              target="_blank"
              rel="noopener noreferrer"
              onClick={() => setApplyViewed(true)}
              className="rounded bg-[#172033] px-3 py-2 text-sm font-medium text-white hover:bg-[#0f1728]"
            >
              Apply / View Job
            </a>
          ) : (
            <button
              type="button"
              disabled
              className="cursor-not-allowed rounded bg-[#d0d5dd] px-3 py-2 text-sm font-medium text-white"
            >
              Apply / View Job
            </button>
          )}
          <Link
            href={`/jobs/${job.job_id}/workspace`}
            className="rounded border border-[#c8ced8] bg-white px-3 py-2 text-sm font-medium text-[#344054] hover:bg-[#f8fafc]"
          >
            Open Workspace
          </Link>
          <WatchCompanyButton
            jobId={job.job_id}
            payload={{
              priority: "medium",
              watch_status: "watching",
              interest_reason: `Interesting ${formatMatchTier(job.match_tier)} role: ${job.title}`,
              target_roles: [job.title, job.role_category].filter(Boolean) as string[],
              remote_interest: remoteInterestFromRecommendation(job.remote_eligibility),
              junior_friendliness_signal: juniorSignalFromSeniority(job.seniority),
            }}
          />
          {applyViewed && onDecisionAction ? (
            <button
              type="button"
              onClick={() =>
                onDecisionAction(job, {
                  decision_status: "applied",
                  priority: decision?.priority ?? "high",
                })
              }
              disabled={decisionPending}
              className="rounded border border-[#c8ced8] bg-white px-3 py-2 text-sm font-medium text-[#344054] hover:bg-[#f8fafc] disabled:cursor-not-allowed disabled:opacity-60"
            >
              Mark as applied
            </button>
          ) : null}
          {onPrepareApplication ? (
            <button
              type="button"
              onClick={() => onPrepareApplication(job)}
              disabled={prepPending}
              className="rounded border border-[#175cd3] bg-white px-3 py-2 text-sm font-medium text-[#175cd3] hover:bg-[#eff6ff] disabled:cursor-not-allowed disabled:opacity-60"
            >
              {prepPending ? "Preparing..." : prep ? "Regenerate Prep" : "Prepare Application"}
            </button>
          ) : null}
          {onGeneratePacket ? (
            <button
              type="button"
              onClick={() => onGeneratePacket(job)}
              disabled={packetPending}
              className="rounded border border-[#166534] bg-white px-3 py-2 text-sm font-medium text-[#166534] hover:bg-[#f0fdf4] disabled:cursor-not-allowed disabled:opacity-60"
            >
              {packetPending
                ? "Generating packet..."
                : packet
                  ? "Regenerate Packet"
                  : "Generate Packet"}
            </button>
          ) : null}
          {onImproveResume ? (
            <button
              type="button"
              onClick={() => onImproveResume(job)}
              disabled={improvementPending}
              className="rounded border border-[#7c3aed] bg-white px-3 py-2 text-sm font-medium text-[#6d28d9] hover:bg-[#f5f3ff] disabled:cursor-not-allowed disabled:opacity-60"
            >
              {improvementPending
                ? "Generating resume suggestions..."
                : improvement
                  ? "Regenerate Resume Suggestions"
                  : "Improve Resume"}
            </button>
          ) : null}
        </div>
      </div>

      {onDecisionAction ? (
        <div className="mt-4 flex flex-wrap gap-2">
          <DecisionButton
            label="Save"
            disabled={decisionPending}
            onClick={() =>
              onDecisionAction(job, {
                decision_status: "saved",
                priority: "medium",
              })
            }
          />
          <DecisionButton
            label="Needs Resume"
            disabled={decisionPending}
            onClick={() =>
              onDecisionAction(job, {
                decision_status: "needs_custom_resume",
                priority: "high",
                next_action: "Tailor resume for this role.",
              })
            }
          />
          <DecisionButton
            label="Needs Cold DM"
            disabled={decisionPending}
            onClick={() =>
              onDecisionAction(job, {
                decision_status: "needs_cold_dm",
                priority: "high",
                next_action:
                  "Find founder or hiring manager and draft cold DM.",
              })
            }
          />
          <DecisionButton
            label="Applied"
            disabled={decisionPending}
            onClick={() =>
              onDecisionAction(job, {
                decision_status: "applied",
                priority: decision?.priority ?? "high",
              })
            }
          />
          <DecisionButton
            label="Skip"
            disabled={decisionPending}
            onClick={() => onDecisionAction(job, { decision_status: "skipped" })}
          />
          <DecisionButton
            label="Not Interested"
            disabled={decisionPending}
            onClick={() =>
              onDecisionAction(job, { decision_status: "not_interested" })
            }
          />
        </div>
      ) : null}

      <dl className="mt-5 grid gap-3 text-sm sm:grid-cols-2 xl:grid-cols-4">
        <Fact label="Remote" value={formatRemoteEligibility(job.remote_eligibility)} />
        <Fact label="Seniority" value={labelize(job.seniority)} />
        <Fact label="Experience" value={formatExperience(job)} />
        <Fact label="Employment" value={labelize(job.employment_type)} />
        <Fact label="Salary" value={salary ?? "No salary listed"} />
        <Fact label="Enrichment" value={labelize(job.enrichment_status)} />
        <Fact label="Role score" value={scoreLabel(job.role_score)} />
        <Fact label="Remote score" value={scoreLabel(job.remote_score)} />
      </dl>

      {job.eligibility_reason ? (
        <p className="mt-4 rounded border border-[#d9dee8] bg-[#f8fafc] px-3 py-2 text-sm leading-6 text-[#344054]">
          {job.eligibility_reason}
        </p>
      ) : null}

      <div className="mt-4 grid gap-3 lg:grid-cols-3">
        <SignalList title="Positive signals" items={job.positive_signals ?? []} />
        <SignalList title="Missing information" items={job.missing_information ?? []} />
        <SignalList title="Negative signals" items={job.negative_signals ?? []} />
      </div>

      {onGeneratePacket && !packet ? (
        <div
          className={[
            "mt-4 rounded border px-3 py-2 text-sm",
            activeResumeParsed
              ? "border-[#bbf7d0] bg-[#f0fdf4] text-[#166534]"
              : "border-[#fed7aa] bg-[#fff7ed] text-[#9a3412]",
          ].join(" ")}
        >
          {activeResumeParsed
            ? "Resume-aware packets available."
            : "Upload resume for better packet suggestions."}
        </div>
      ) : null}

      {decision ? (
        <div className="mt-4 rounded border border-[#edf0f5] bg-[#fcfcfd] p-3">
          <div className="grid gap-3 md:grid-cols-[1fr_1fr_160px_auto] md:items-end">
            <label className="text-sm text-[#344054]">
              <span className="mb-1 block text-xs font-medium uppercase tracking-normal text-[#667085]">
                Notes
              </span>
              <textarea
                value={notes}
                onChange={(event) => setNotes(event.target.value)}
                rows={2}
                className="w-full rounded border border-[#c8ced8] bg-white px-3 py-2 text-sm"
              />
            </label>
            <label className="text-sm text-[#344054]">
              <span className="mb-1 block text-xs font-medium uppercase tracking-normal text-[#667085]">
                Next action
              </span>
              <textarea
                value={nextAction}
                onChange={(event) => setNextAction(event.target.value)}
                rows={2}
                className="w-full rounded border border-[#c8ced8] bg-white px-3 py-2 text-sm"
              />
            </label>
            <label className="text-sm text-[#344054]">
              <span className="mb-1 block text-xs font-medium uppercase tracking-normal text-[#667085]">
                Priority
              </span>
              <select
                value={priority}
                onChange={(event) => setPriority(event.target.value)}
                className="w-full rounded border border-[#c8ced8] bg-white px-3 py-2 text-sm"
              >
                {["low", "medium", "high", "urgent"].map((item) => (
                  <option key={item} value={item}>
                    {labelize(item)}
                  </option>
                ))}
              </select>
            </label>
            <button
              type="button"
              onClick={() =>
                onDecisionUpdate?.(decision, {
                  notes,
                  next_action: nextAction,
                  priority,
                })
              }
              disabled={decisionPending}
              className="rounded bg-[#172033] px-3 py-2 text-sm font-medium text-white disabled:cursor-not-allowed disabled:opacity-60"
            >
              Save notes
            </button>
          </div>
        </div>
      ) : null}

      {prepError ? (
        <div className="mt-4 rounded border border-[#fecaca] bg-[#fff7f7] p-3 text-sm text-[#991b1b]">
          <div className="font-medium">Could not prepare application notes.</div>
          <p className="mt-1">{prepError}</p>
          {onPrepareApplication ? (
            <button
              type="button"
              onClick={() => onPrepareApplication(job)}
              className="mt-3 rounded bg-[#172033] px-3 py-2 text-sm font-medium text-white"
            >
              Retry
            </button>
          ) : null}
        </div>
      ) : null}

      {prep ? <ApplicationPrepPanel prep={prep} /> : null}

      {!packet && !packetPending && !packetError && onGeneratePacket ? (
        <p className="mt-4 rounded border border-[#edf0f5] bg-[#fcfcfd] px-3 py-2 text-sm text-[#667085]">
          Generate a tailored packet before applying.
        </p>
      ) : null}

      {packetError ? (
        <div className="mt-4 rounded border border-[#fecaca] bg-[#fff7f7] p-3 text-sm text-[#991b1b]">
          <div className="font-medium">Could not generate application packet.</div>
          <p className="mt-1">{packetError}</p>
          {onGeneratePacket ? (
            <button
              type="button"
              onClick={() => onGeneratePacket(job)}
              className="mt-3 rounded bg-[#172033] px-3 py-2 text-sm font-medium text-white"
            >
              Retry
            </button>
          ) : null}
        </div>
      ) : null}

      {packet ? <ApplicationPacketPanel packet={packet} /> : null}

      {improvementError ? (
        <div className="mt-4 rounded border border-[#fecaca] bg-[#fff7f7] p-3 text-sm text-[#991b1b]">
          <div className="font-medium">Could not generate resume improvement suggestions.</div>
          <p className="mt-1">{improvementError}</p>
          {onImproveResume ? (
            <button
              type="button"
              onClick={() => onImproveResume(job)}
              className="mt-3 rounded bg-[#172033] px-3 py-2 text-sm font-medium text-white"
            >
              Retry
            </button>
          ) : null}
        </div>
      ) : null}

      {improvement ? <ResumeImprovementPanel improvement={improvement} /> : null}

      <div className="mt-4 flex flex-wrap items-center justify-between gap-3 border-t border-[#edf0f5] pt-3 text-xs text-[#667085]">
        {attribution.url ? (
          <a
            href={attribution.url}
            target="_blank"
            rel="noopener noreferrer"
            className="font-medium text-[#175cd3] hover:underline"
          >
            {attribution.label}
          </a>
        ) : (
          <span>{attribution.label}</span>
        )}
        <span>Scored {formatDate(job.scored_at)}</span>
      </div>
    </article>
  );
}

function DecisionButton({
  label,
  disabled,
  onClick,
}: {
  label: string;
  disabled: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      className="rounded border border-[#c8ced8] bg-white px-3 py-1.5 text-sm font-medium text-[#344054] hover:bg-[#f8fafc] disabled:cursor-not-allowed disabled:opacity-60"
    >
      {label}
    </button>
  );
}

function Fact({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-xs font-medium uppercase tracking-normal text-[#667085]">
        {label}
      </dt>
      <dd className="mt-1 text-[#344054]">{value}</dd>
    </div>
  );
}

function SignalList({ title, items }: { title: string; items: string[] }) {
  return (
    <div className="rounded border border-[#edf0f5] bg-[#fcfcfd] p-3">
      <h3 className="text-xs font-semibold uppercase tracking-normal text-[#667085]">
        {title}
      </h3>
      {items.length > 0 ? (
        <ul className="mt-2 space-y-1 text-sm text-[#344054]">
          {items.slice(0, 4).map((item) => (
            <li key={item}>- {labelize(item)}</li>
          ))}
        </ul>
      ) : (
        <p className="mt-2 text-sm text-[#98a2b3]">None listed</p>
      )}
    </div>
  );
}

function Badge({
  children,
  tone,
}: {
  children: string;
  tone: "success" | "info" | "warning" | "danger" | "neutral";
}) {
  const classes = {
    success: "border-[#bbf7d0] bg-[#f0fdf4] text-[#166534]",
    info: "border-[#bfdbfe] bg-[#eff6ff] text-[#1d4ed8]",
    warning: "border-[#fed7aa] bg-[#fff7ed] text-[#9a3412]",
    danger: "border-[#fecaca] bg-[#fff7f7] text-[#991b1b]",
    neutral: "border-[#e5e7eb] bg-[#f8fafc] text-[#475467]",
  }[tone];

  return (
    <span className={`inline-flex rounded-full border px-2 py-0.5 text-xs font-medium ${classes}`}>
      {children}
    </span>
  );
}

function tierTone(tier: string): "success" | "info" | "warning" | "danger" | "neutral" {
  if (tier === "best_match" || tier === "strong_match") {
    return "success";
  }
  if (tier === "worth_checking") {
    return "info";
  }
  if (tier === "stretch") {
    return "warning";
  }
  if (tier === "unsuitable") {
    return "danger";
  }
  return "neutral";
}

function eligibilityTone(value: string): "success" | "info" | "warning" | "danger" | "neutral" {
  if (value === "eligible") {
    return "success";
  }
  if (value === "stretch" || value === "uncertain") {
    return "warning";
  }
  if (value === "unsuitable") {
    return "danger";
  }
  return "neutral";
}

export function decisionStatusLabel(value: JobDecisionStatus) {
  return (
    {
      saved: "Saved",
      interested: "Interested",
      needs_custom_resume: "Needs Resume",
      needs_cold_dm: "Needs Cold DM",
      applied: "Applied",
      skipped: "Skipped",
      not_interested: "Not Interested",
      interviewing: "Interviewing",
      rejected: "Rejected",
      offer: "Offer",
      archived: "Archived",
      dismissed: "Skipped",
    }[value] ?? labelize(value)
  );
}

function decisionTone(
  value: JobDecisionStatus,
): "success" | "info" | "warning" | "danger" | "neutral" {
  if (value === "applied" || value === "interviewing" || value === "offer") {
    return "success";
  }
  if (value === "saved" || value === "interested") {
    return "info";
  }
  if (value === "needs_custom_resume" || value === "needs_cold_dm") {
    return "warning";
  }
  if (value === "not_interested" || value === "rejected" || value === "dismissed") {
    return "danger";
  }
  return "neutral";
}

function scoreLabel(value: number | null | undefined) {
  return value == null ? "Not scored" : String(Math.round(value));
}

function remoteInterestFromRecommendation(value: string | null | undefined) {
  if (value === "work_from_anywhere") return "remote_worldwide";
  if (value === "remote_india_eligible") return "remote_india";
  if (value === "hybrid") return "hybrid_possible";
  return "unknown";
}

function juniorSignalFromSeniority(value: string | null | undefined) {
  if (!value) return "unknown";
  return /intern|junior|entry|new_grad|graduate/i.test(value) ? "strong" : "unknown";
}

function formatDate(value: string | null | undefined) {
  if (!value) {
    return "recently";
  }
  return new Intl.DateTimeFormat("en", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}
