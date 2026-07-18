"use client";

import Link from "next/link";
import { useState } from "react";

import { sourceLabels } from "@/components/discovery/DiscoverySourceSelector";
import type { DailyScoutPayloadResult } from "@/lib/daily-scout";
import type { SourceQualityAdvisorItem } from "@/lib/source-quality-advisor";

export function DailyScoutPanel({
  payloadResult,
  advisors,
  includeWeeklyManualSources,
  running,
  phaseText,
  onIncludeWeeklyManualSourcesChange,
  onRunDailyScout,
  onPreviewPayload,
  onSelectAdvisorDaily,
  onSelectSafeDefaults,
  onSelectAllAvailable,
  onRunManualSelection,
}: {
  payloadResult: DailyScoutPayloadResult;
  advisors: SourceQualityAdvisorItem[];
  includeWeeklyManualSources: boolean;
  running: boolean;
  phaseText: string | null;
  onIncludeWeeklyManualSourcesChange: (value: boolean) => void;
  onRunDailyScout: () => void;
  onPreviewPayload: () => void;
  onSelectAdvisorDaily: () => void;
  onSelectSafeDefaults: () => void;
  onSelectAllAvailable: () => void;
  onRunManualSelection: () => void;
}) {
  const dailySources = advisors.filter((advisor) =>
    ["run_daily", "run_every_few_days"].includes(advisor.recommendation),
  );
  const manualSources = advisors.filter((advisor) =>
    ["run_weekly", "run_manually"].includes(advisor.recommendation),
  );
  const attentionSources = advisors.filter((advisor) =>
    ["needs_configuration", "needs_debugging"].includes(advisor.recommendation),
  );

  return (
    <section className="mb-5 rounded-md border border-[#d9dee8] bg-white p-5">
      <div className="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
        <div>
          <h2 className="text-lg font-semibold text-[#171923]">Daily Scout</h2>
          <p className="mt-1 text-sm text-[#667085]">
            Run the best discovery sources for your profile using the latest source quality signals.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            onClick={onRunDailyScout}
            disabled={running || !payloadResult.selectedSources.length}
            className="rounded bg-[#172033] px-4 py-2 text-sm font-medium text-white hover:bg-[#0f1728] disabled:cursor-not-allowed disabled:opacity-60"
          >
            {running ? "Running Daily Scout..." : "Run Daily Scout"}
          </button>
          <button type="button" onClick={onPreviewPayload} className="rounded border border-[#c8ced8] px-3 py-2 text-sm font-medium text-[#344054] hover:bg-[#f8fafc]">
            Preview Payload
          </button>
          <button type="button" onClick={onSelectAdvisorDaily} className="rounded border border-[#c8ced8] px-3 py-2 text-sm font-medium text-[#344054] hover:bg-[#f8fafc]">
            Select Sources Manually
          </button>
          <button
            type="button"
            onClick={onRunManualSelection}
            disabled={running}
            className="rounded border border-[#c8ced8] px-3 py-2 text-sm font-medium text-[#344054] hover:bg-[#f8fafc] disabled:cursor-not-allowed disabled:opacity-60"
          >
            Run Manual Selection
          </button>
        </div>
      </div>

      {phaseText ? (
        <div className="mt-4 rounded border border-[#bfdbfe] bg-[#eff6ff] px-3 py-2 text-sm font-medium text-[#1d4ed8]">
          {phaseText}
        </div>
      ) : null}

      {payloadResult.fallbackReason ? (
        <div className="mt-4 rounded border border-[#fedf89] bg-[#fffbeb] px-3 py-2 text-sm text-[#92400e]">
          {payloadResult.fallbackReason}
        </div>
      ) : null}

      {includeWeeklyManualSources ? (
        <div className="mt-4 rounded border border-[#fedf89] bg-[#fffbeb] px-3 py-2 text-sm text-[#92400e]">
          Weekly/manual sources may be noisier or slower.
        </div>
      ) : null}

      {payloadResult.riskyWarnings.length ? (
        <div className="mt-4 rounded border border-[#fedf89] bg-[#fffbeb] p-3 text-sm text-[#92400e]">
          <p className="font-semibold">Before running</p>
          <ul className="mt-1 list-disc space-y-1 pl-5">
            {payloadResult.riskyWarnings.map((warning) => (
              <li key={warning}>{warning}</li>
            ))}
          </ul>
        </div>
      ) : null}

      <div className="mt-5 grid gap-3 lg:grid-cols-4">
        <SourceBucket title="Recommended daily sources" sources={dailySources.map((item) => item.source)} />
        <SourceBucket title="Manual / weekly sources" sources={manualSources.map((item) => item.source)} />
        <SourceBucket title="Needs attention" sources={attentionSources.map((item) => item.source)} />
        <SourceBucket title="Selected for Daily Scout" sources={payloadResult.selectedSources} />
      </div>

      <div className="mt-4 flex flex-wrap items-center gap-2">
        <label className="flex items-center gap-2 text-sm text-[#344054]">
          <input
            type="checkbox"
            checked={includeWeeklyManualSources}
            onChange={(event) => onIncludeWeeklyManualSourcesChange(event.target.checked)}
            className="h-4 w-4 accent-[#172033]"
          />
          Include weekly/manual sources
        </label>
        <button type="button" onClick={onSelectAdvisorDaily} className="rounded border border-[#c8ced8] px-3 py-2 text-sm font-medium text-[#344054] hover:bg-[#f8fafc]">
          Use advisor recommended daily set
        </button>
        <button type="button" onClick={onSelectSafeDefaults} className="rounded border border-[#c8ced8] px-3 py-2 text-sm font-medium text-[#344054] hover:bg-[#f8fafc]">
          Use safe default set
        </button>
        <button type="button" onClick={onSelectAllAvailable} className="rounded border border-[#c8ced8] px-3 py-2 text-sm font-medium text-[#344054] hover:bg-[#f8fafc]">
          Use all available sources
        </button>
      </div>

      <p className="mt-4 text-sm text-[#667085]">
        Estimated behavior is based on local run history: enrichment, scoring, warnings, failures, and duration.
      </p>
    </section>
  );
}

export function PayloadPreviewDrawer({
  payload,
  error,
  copied,
  onCopy,
  onRun,
  onClose,
}: {
  payload: unknown;
  error: string | null;
  copied: boolean;
  onCopy: () => void;
  onRun: () => void;
  onClose: () => void;
}) {
  const [showRaw, setShowRaw] = useState(true);
  const object = payload && typeof payload === "object" ? (payload as { sources?: unknown }) : {};
  const sources = Array.isArray(object.sources) ? object.sources.map(String) : [];

  return (
    <div className="fixed inset-0 z-40 bg-[#101828]/30">
      <div className="absolute right-0 top-0 h-full w-full max-w-2xl overflow-y-auto bg-white p-5 shadow-xl">
        <div className="mb-5 flex items-start justify-between gap-4">
          <div>
            <h2 className="text-lg font-semibold text-[#171923]">Daily Scout Payload</h2>
            <p className="mt-1 text-sm text-[#667085]">Review the unified discovery request before running.</p>
          </div>
          <button type="button" onClick={onClose} className="rounded border border-[#c8ced8] px-3 py-2 text-sm font-medium text-[#344054] hover:bg-[#f8fafc]">
            Close
          </button>
        </div>

        <div className="rounded border border-[#e4e7ec] bg-[#fcfcfd] p-3">
          <p className="text-xs font-medium uppercase tracking-normal text-[#667085]">Selected sources</p>
          <p className="mt-1 text-sm font-semibold text-[#171923]">
            {sources.length ? sources.map((source) => sourceLabels[source] ?? source).join(", ") : "No sources selected"}
          </p>
        </div>

        <div className="mt-4 flex flex-wrap gap-2">
          <button type="button" onClick={onCopy} className="rounded border border-[#c8ced8] px-3 py-2 text-sm font-medium text-[#344054] hover:bg-[#f8fafc]">
            Copy Payload
          </button>
          <button type="button" onClick={onRun} className="rounded bg-[#172033] px-3 py-2 text-sm font-medium text-white hover:bg-[#0f1728]">
            Run This Payload
          </button>
          <button type="button" onClick={() => setShowRaw((value) => !value)} className="rounded border border-[#c8ced8] px-3 py-2 text-sm font-medium text-[#344054] hover:bg-[#f8fafc]">
            {showRaw ? "Hide Raw JSON" : "Show Raw JSON"}
          </button>
        </div>

        {copied ? <p className="mt-3 text-sm text-[#166534]">Payload copied.</p> : null}
        {error ? <p className="mt-3 text-sm text-[#991b1b]">{error}</p> : null}

        {showRaw ? (
          <pre className="mt-4 max-h-[70vh] overflow-auto rounded bg-[#101828] p-4 text-xs leading-5 text-white">
            {JSON.stringify(payload, null, 2)}
          </pre>
        ) : null}
      </div>
    </div>
  );
}

export function DailyScoutNextActions({
  onCompareRuns,
  onRunManualSources,
}: {
  onCompareRuns: () => void;
  onRunManualSources: () => void;
}) {
  return (
    <section className="rounded-md border border-[#d9dee8] bg-white p-5">
      <h2 className="text-base font-semibold text-[#171923]">Next Actions</h2>
      <div className="mt-4 flex flex-wrap gap-2">
        <Link href="/recommendations" className="rounded bg-[#172033] px-3 py-2 text-sm font-medium text-white hover:bg-[#0f1728]">
          Review top recommendations
        </Link>
        <Link href="/jobs/pipeline" className="rounded border border-[#c8ced8] px-3 py-2 text-sm font-medium text-[#344054] hover:bg-[#f8fafc]">
          Open job pipeline
        </Link>
        <Link href="/companies/watchlist" className="rounded border border-[#c8ced8] px-3 py-2 text-sm font-medium text-[#344054] hover:bg-[#f8fafc]">
          Open company watchlist
        </Link>
        <button type="button" onClick={onCompareRuns} className="rounded border border-[#c8ced8] px-3 py-2 text-sm font-medium text-[#344054] hover:bg-[#f8fafc]">
          Compare source runs
        </button>
        <button type="button" onClick={onRunManualSources} className="rounded border border-[#c8ced8] px-3 py-2 text-sm font-medium text-[#344054] hover:bg-[#f8fafc]">
          Re-run with manual sources
        </button>
      </div>
    </section>
  );
}

function SourceBucket({ title, sources }: { title: string; sources: string[] }) {
  return (
    <div className="rounded border border-[#e4e7ec] bg-[#fcfcfd] p-3">
      <p className="text-xs font-medium uppercase tracking-normal text-[#667085]">{title}</p>
      {sources.length ? (
        <div className="mt-2 flex flex-wrap gap-2">
          {sources.map((source) => (
            <span key={source} className="rounded border border-[#d9dee8] bg-white px-2 py-1 text-xs font-medium text-[#475467]">
              {sourceLabels[source] ?? source}
            </span>
          ))}
        </div>
      ) : (
        <p className="mt-2 text-sm text-[#667085]">None yet</p>
      )}
    </div>
  );
}
