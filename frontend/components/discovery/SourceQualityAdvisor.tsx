"use client";

import { useState } from "react";

import { formatDuration } from "@/components/discovery/DiscoveryRunSummary";
import {
  recommendationLabel,
  type SourceQualityAdvisorItem,
  type SourceRecommendation,
} from "@/lib/source-quality-advisor";

export function SourceQualityAdvisor({
  advisors,
  onSelectSources,
}: {
  advisors: SourceQualityAdvisorItem[];
  onSelectSources: (sources: string[]) => void;
}) {
  const [showExplanation, setShowExplanation] = useState(false);
  const dailySources = advisors
    .filter((item) => ["run_daily", "run_every_few_days"].includes(item.recommendation))
    .map((item) => item.source);
  const manualSources = advisors
    .filter((item) => ["run_weekly", "run_manually"].includes(item.recommendation))
    .map((item) => item.source);
  const noisySources = advisors
    .filter((item) => (item.noiseScore ?? 0) >= 50 || ["needs_configuration", "needs_debugging"].includes(item.recommendation))
    .map((item) => item.source);

  return (
    <section className="rounded-md border border-[#d9dee8] bg-white p-5">
      <div className="mb-5 flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <h2 className="text-base font-semibold text-[#171923]">Source Quality Advisor</h2>
          <p className="mt-1 text-sm text-[#667085]">
            ScoutAI analyzes recent runs and recommends which sources are worth using.
          </p>
        </div>
        <button
          type="button"
          onClick={() => setShowExplanation((value) => !value)}
          className="self-start rounded border border-[#c8ced8] px-3 py-2 text-sm font-medium text-[#344054] hover:bg-[#f8fafc]"
        >
          How ScoutAI decides this
        </button>
      </div>

      {showExplanation ? (
        <div className="mb-5 rounded border border-[#e4e7ec] bg-[#fcfcfd] p-4 text-sm text-[#475467]">
          Quality score uses enrichment, scoring, failures, warnings, conversion into jobs, and duration.
          Noise score uses rejected/deferred candidates, unresolved or unenriched work, failed jobs, and warnings.
          Recommendations are deterministic and based only on local run history plus the latest run response.
        </div>
      ) : null}

      <RecommendedDailySourceSet
        dailySources={dailySources}
        manualSources={manualSources}
        attentionSources={advisors
          .filter((item) => ["needs_configuration", "needs_debugging"].includes(item.recommendation))
          .map((item) => item.source)}
        noisySources={noisySources}
        advisors={advisors}
        onSelectSources={onSelectSources}
      />

      {advisors.length ? (
        <div className="mt-5 grid gap-4 xl:grid-cols-2">
          {advisors.map((advisor) => (
            <SourceQualityAdvisorCard key={advisor.source} advisor={advisor} />
          ))}
        </div>
      ) : (
        <div className="mt-5 rounded border border-[#e4e7ec] bg-[#fcfcfd] p-4 text-sm text-[#667085]">
          No discovery sources are available yet.
        </div>
      )}
    </section>
  );
}

export function RecommendedDailySourceSet({
  dailySources,
  manualSources,
  attentionSources,
  noisySources,
  advisors,
  onSelectSources,
}: {
  dailySources: string[];
  manualSources: string[];
  attentionSources: string[];
  noisySources: string[];
  advisors: SourceQualityAdvisorItem[];
  onSelectSources: (sources: string[]) => void;
}) {
  return (
    <div className="grid gap-3 lg:grid-cols-3">
      <SourceSetCard
        title="Recommended daily run"
        sources={dailySources}
        advisors={advisors}
        emptyText="Not enough strong daily signal yet."
        actionLabel="Select recommended daily sources"
        onSelectSources={onSelectSources}
      />
      <SourceSetCard
        title="Manual / weekly sources"
        sources={manualSources}
        advisors={advisors}
        emptyText="No manual or weekly sources flagged."
        actionLabel="Select manual sources"
        onSelectSources={onSelectSources}
      />
      <SourceSetCard
        title="Needs attention"
        sources={attentionSources}
        advisors={advisors}
        emptyText="No source needs immediate attention."
        actionLabel="Select noisy sources"
        overrideSources={noisySources}
        onSelectSources={onSelectSources}
      />
    </div>
  );
}

export function SourceQualityAdvisorCard({
  advisor,
}: {
  advisor: SourceQualityAdvisorItem;
}) {
  return (
    <article className="rounded border border-[#e4e7ec] bg-[#fcfcfd] p-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h3 className="text-base font-semibold text-[#171923]">{advisor.displayName}</h3>
          <p className="mt-1 text-sm text-[#667085]">{advisor.recommendationReason}</p>
        </div>
        <span className={`self-start rounded border px-2.5 py-1 text-xs font-semibold ${recommendationTone(advisor.recommendation)}`}>
          {recommendationLabel(advisor.recommendation)}
        </span>
      </div>

      <div className="mt-4 grid gap-3 sm:grid-cols-2">
        <ScoreBar label="Quality score" value={advisor.qualityScore} tone="green" />
        <ScoreBar label="Noise score" value={advisor.noiseScore} tone="amber" />
      </div>

      <div className="mt-4 grid gap-2 text-sm text-[#475467] sm:grid-cols-2">
        <Metric label="Suggested cadence" value={advisor.suggestedCadence} />
        <Metric label="Total runs" value={advisor.totalRuns} />
        <Metric label="Jobs scored" value={advisor.totalJobsScored} />
        <Metric label="Jobs enriched" value={advisor.totalJobsEnriched} />
        <Metric label="Average duration" value={advisor.averageDurationMs === null ? "—" : formatDuration(advisor.averageDurationMs)} />
        <Metric label="Failure rate" value={`${Math.round(advisor.failureRate * 100)}%`} />
      </div>

      <div className="mt-4 grid gap-3 md:grid-cols-2">
        <TextList title="Strengths" items={advisor.strengths} emptyText="No strengths detected yet." />
        <TextList title="Issues" items={advisor.issues} emptyText="No issues detected yet." />
      </div>
    </article>
  );
}

function SourceSetCard({
  title,
  sources,
  advisors,
  emptyText,
  actionLabel,
  overrideSources,
  onSelectSources,
}: {
  title: string;
  sources: string[];
  advisors: SourceQualityAdvisorItem[];
  emptyText: string;
  actionLabel: string;
  overrideSources?: string[];
  onSelectSources: (sources: string[]) => void;
}) {
  const actionSources = overrideSources ?? sources;
  return (
    <div className="rounded border border-[#e4e7ec] bg-[#fcfcfd] p-4">
      <h3 className="text-sm font-semibold text-[#344054]">{title}</h3>
      {sources.length ? (
        <div className="mt-3 flex flex-wrap gap-2">
          {sources.map((source) => (
            <span key={source} className="rounded border border-[#d9dee8] bg-white px-2.5 py-1 text-xs font-medium text-[#475467]">
              {advisors.find((item) => item.source === source)?.displayName ?? source}
            </span>
          ))}
        </div>
      ) : (
        <p className="mt-3 text-sm text-[#667085]">{emptyText}</p>
      )}
      <button
        type="button"
        disabled={!actionSources.length}
        onClick={() => onSelectSources(actionSources)}
        className="mt-4 rounded border border-[#c8ced8] px-3 py-2 text-sm font-medium text-[#344054] hover:bg-[#f8fafc] disabled:cursor-not-allowed disabled:opacity-60"
      >
        {actionLabel}
      </button>
    </div>
  );
}

function ScoreBar({
  label,
  value,
  tone,
}: {
  label: string;
  value: number | null;
  tone: "green" | "amber";
}) {
  const width = value === null ? 0 : Math.max(4, Math.min(100, value));
  const color = tone === "green" ? "bg-[#16a34a]" : "bg-[#d97706]";
  return (
    <div>
      <div className="mb-1 flex justify-between text-xs text-[#667085]">
        <span>{label}</span>
        <span>{value === null ? "Not enough data" : `${value}/100`}</span>
      </div>
      <div className="h-2 rounded bg-[#eef2f6]">
        <div className={`h-2 rounded ${color}`} style={{ width: `${value === null ? 0 : width}%` }} />
      </div>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="flex justify-between gap-3">
      <span>{label}</span>
      <span className="font-semibold text-[#171923]">{value}</span>
    </div>
  );
}

function TextList({
  title,
  items,
  emptyText,
}: {
  title: string;
  items: string[];
  emptyText: string;
}) {
  return (
    <div>
      <h4 className="text-sm font-semibold text-[#344054]">{title}</h4>
      {items.length ? (
        <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-[#667085]">
          {items.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      ) : (
        <p className="mt-2 text-sm text-[#667085]">{emptyText}</p>
      )}
    </div>
  );
}

function recommendationTone(recommendation: SourceRecommendation) {
  if (recommendation === "run_daily" || recommendation === "run_every_few_days") {
    return "border-[#bbf7d0] bg-[#f0fdf4] text-[#166534]";
  }
  if (recommendation === "run_weekly" || recommendation === "run_manually") {
    return "border-[#fedf89] bg-[#fffbeb] text-[#92400e]";
  }
  if (recommendation === "needs_configuration" || recommendation === "needs_debugging") {
    return "border-[#fecaca] bg-[#fff7f7] text-[#991b1b]";
  }
  return "border-[#d9dee8] bg-white text-[#475467]";
}
