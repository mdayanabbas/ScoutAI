"use client";

import Link from "next/link";

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
import type { RecommendedJobMatch } from "@/types/job-match";

export function RecommendedJobCard({ job }: { job: RecommendedJobMatch }) {
  const salary = formatSalary(job);
  const applyUrl = applyUrlForJob(job);
  const attribution = sourceAttribution(job.job_url);
  const unsuitable = job.eligibility_status === "unsuitable";
  const remoteUnverified =
    job.remote_eligibility === "unknown" ||
    job.remote_eligibility === "remote_eligibility_unclear";

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
        </div>
      </div>

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

function scoreLabel(value: number | null | undefined) {
  return value == null ? "Not scored" : String(Math.round(value));
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
