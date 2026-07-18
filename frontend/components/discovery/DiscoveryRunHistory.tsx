"use client";

import { useMemo, useState } from "react";

import { sourceLabels } from "@/components/discovery/DiscoverySourceSelector";
import { StatusBadge, formatDuration } from "@/components/discovery/DiscoveryRunSummary";
import type { DiscoveryRunListItem } from "@/types/discovery";

type TimeFilter = "all" | "24h" | "7d";

export function DiscoveryRunHistory({
  loading,
  error,
  runs,
  selectedRunIds,
  compareActive,
  compareMessage,
  running,
  rerunMessage,
  onRefresh,
  onOpenDetails,
  onToggleCompare,
  onCompare,
  onRerunSource,
}: {
  loading: boolean;
  error: boolean;
  runs: DiscoveryRunListItem[];
  selectedRunIds: string[];
  compareActive: boolean;
  compareMessage: string | null;
  running: boolean;
  rerunMessage: string | null;
  onRefresh: () => void;
  onOpenDetails: (run: DiscoveryRunListItem) => void;
  onToggleCompare: (runId: string) => void;
  onCompare: () => void;
  onRerunSource: (run: DiscoveryRunListItem) => void;
}) {
  const [sourceFilter, setSourceFilter] = useState("all");
  const [statusFilter, setStatusFilter] = useState("all");
  const [timeFilter, setTimeFilter] = useState<TimeFilter>("all");
  const [failedOnly, setFailedOnly] = useState(false);
  const [partialOnly, setPartialOnly] = useState(false);

  const sources = useMemo(
    () =>
      Array.from(new Set(runs.map((run) => stringValue(run.source)).filter(Boolean) as string[]))
        .sort((a, b) => a.localeCompare(b)),
    [runs],
  );

  const filteredRuns = useMemo(
    () =>
      runs.filter((run) => {
        const source = stringValue(run.source) ?? "";
        const status = stringValue(run.status) ?? "";
        if (sourceFilter !== "all" && source !== sourceFilter) return false;
        if (statusFilter !== "all" && status !== statusFilter) return false;
        if (failedOnly && status !== "failed") return false;
        if (partialOnly && status !== "partial") return false;
        if (!withinTimeFilter(run, timeFilter)) return false;
        return true;
      }),
    [failedOnly, partialOnly, runs, sourceFilter, statusFilter, timeFilter],
  );

  const maxJobsScored = Math.max(1, ...filteredRuns.map((run) => numberValue(run.jobs_scored) ?? 0));
  const maxCandidatesCreated = Math.max(1, ...filteredRuns.map((run) => numberValue(run.candidates_created) ?? 0));
  const maxNoise = Math.max(
    1,
    ...filteredRuns.map((run) => warningCount(run) + (numberValue(run.jobs_failed) ?? 0)),
  );

  return (
    <aside className="rounded-md border border-[#d9dee8] bg-white p-5">
      <div className="mb-4 flex items-start justify-between gap-3">
        <div>
          <h2 className="text-base font-semibold text-[#171923]">Recent Discovery Runs</h2>
          <p className="mt-1 text-sm text-[#667085]">Filter, inspect, compare, or re-run recent source runs.</p>
        </div>
        <button
          type="button"
          onClick={onRefresh}
          className="rounded border border-[#c8ced8] px-3 py-2 text-sm font-medium text-[#344054] hover:bg-[#f8fafc]"
        >
          Refresh
        </button>
      </div>

      <div className="grid gap-2 sm:grid-cols-2">
        <select value={sourceFilter} onChange={(event) => setSourceFilter(event.target.value)} className="rounded border border-[#c8ced8] px-3 py-2 text-sm text-[#344054]">
          <option value="all">All sources</option>
          {sources.map((source) => (
            <option key={source} value={source}>{sourceLabels[source] ?? source}</option>
          ))}
        </select>
        <select value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)} className="rounded border border-[#c8ced8] px-3 py-2 text-sm text-[#344054]">
          <option value="all">All statuses</option>
          <option value="succeeded">Succeeded</option>
          <option value="partial">Partial</option>
          <option value="failed">Failed</option>
          <option value="skipped">Skipped</option>
        </select>
        <select value={timeFilter} onChange={(event) => setTimeFilter(event.target.value as TimeFilter)} className="rounded border border-[#c8ced8] px-3 py-2 text-sm text-[#344054]">
          <option value="all">All time</option>
          <option value="24h">Last 24 hours</option>
          <option value="7d">Last 7 days</option>
        </select>
        <div className="flex flex-wrap items-center gap-3 rounded border border-[#e4e7ec] px-3 py-2">
          <label className="flex items-center gap-2 text-sm text-[#344054]">
            <input type="checkbox" checked={failedOnly} onChange={(event) => setFailedOnly(event.target.checked)} className="h-4 w-4 accent-[#172033]" />
            Failed only
          </label>
          <label className="flex items-center gap-2 text-sm text-[#344054]">
            <input type="checkbox" checked={partialOnly} onChange={(event) => setPartialOnly(event.target.checked)} className="h-4 w-4 accent-[#172033]" />
            Partial only
          </label>
        </div>
      </div>

      <div className="mt-4 flex flex-wrap items-center justify-between gap-2">
        <p className="text-sm text-[#667085]">{filteredRuns.length} shown</p>
        <button
          type="button"
          onClick={onCompare}
          disabled={selectedRunIds.length < 2}
          className="rounded bg-[#172033] px-3 py-2 text-sm font-medium text-white hover:bg-[#0f1728] disabled:cursor-not-allowed disabled:opacity-60"
        >
          {compareActive ? "Update Compare" : "Compare Runs"}
        </button>
      </div>
      {compareMessage ? <p className="mt-2 text-sm text-[#92400e]">{compareMessage}</p> : null}
      {rerunMessage ? <p className="mt-2 text-sm text-[#175cd3]">{rerunMessage}</p> : null}

      {loading ? <p className="mt-4 text-sm text-[#667085]">Loading runs...</p> : null}
      {error ? <p className="mt-4 text-sm text-[#991b1b]">Could not load recent discovery runs.</p> : null}
      {!loading && !error && !filteredRuns.length ? (
        <p className="mt-4 text-sm text-[#667085]">No discovery runs match these filters.</p>
      ) : null}

      <div className="mt-4 space-y-3">
        {filteredRuns.map((run, index) => {
          const id = runId(run);
          const source = stringValue(run.source) ?? "unknown";
          const selected = Boolean(id && selectedRunIds.includes(id));
          const compareDisabled = Boolean(!selected && selectedRunIds.length >= 5);
          const jobsScored = numberValue(run.jobs_scored) ?? 0;
          const candidatesCreated = numberValue(run.candidates_created) ?? 0;
          const noise = warningCount(run) + (numberValue(run.jobs_failed) ?? 0);

          return (
            <article key={id ?? index} className="rounded border border-[#e4e7ec] bg-[#fcfcfd] p-3">
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    {id ? (
                      <input
                        type="checkbox"
                        checked={selected}
                        disabled={compareDisabled}
                        onChange={() => onToggleCompare(id)}
                        className="h-4 w-4 accent-[#172033]"
                        aria-label={`Select ${id} for comparison`}
                      />
                    ) : null}
                    <p className="text-sm font-semibold text-[#171923]">
                      {sourceLabels[source] ?? source}
                    </p>
                    <StatusBadge status={run.status} />
                  </div>
                  <p className="mt-1 text-xs text-[#667085]">
                    Started {formatDate(run.started_at)} / Finished {formatDate(run.finished_at)}
                  </p>
                  <p className="mt-1 text-xs text-[#667085]">
                    Duration {formatRunDuration(run)} / Warnings {warningCount(run)}
                  </p>
                </div>
                <div className="flex shrink-0 flex-col gap-2">
                  {id ? (
                    <button type="button" onClick={() => onOpenDetails(run)} className="text-xs font-medium text-[#175cd3]">
                      View Details
                    </button>
                  ) : null}
                  <button
                    type="button"
                    onClick={() => onRerunSource(run)}
                    disabled={running || !source}
                    className="text-xs font-medium text-[#175cd3] disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    Re-run Source
                  </button>
                </div>
              </div>

              <div className="mt-3 grid gap-2 text-xs text-[#475467]">
                <MetricLine label="Candidates found" value={numberValue(run.candidates_found)} />
                <MetricLine label="Candidates created" value={candidatesCreated} />
                <MetricLine label="Candidates rejected" value={numberValue(run.candidates_rejected)} />
                <MetricLine label="Jobs created" value={numberValue(run.jobs_created)} />
                <MetricLine label="Jobs existing" value={numberValue(run.jobs_existing)} />
                <MetricLine label="Jobs scored" value={jobsScored} />
                <MetricLine label="Jobs failed" value={numberValue(run.jobs_failed)} />
              </div>

              <div className="mt-3 space-y-2">
                <Indicator label="Jobs scored" value={jobsScored} max={maxJobsScored} tone="blue" />
                <Indicator label="Candidates created" value={candidatesCreated} max={maxCandidatesCreated} tone="green" />
                <Indicator label="Warnings/failures" value={noise} max={maxNoise} tone="amber" />
              </div>
            </article>
          );
        })}
      </div>
    </aside>
  );
}

function MetricLine({ label, value }: { label: string; value: number | null }) {
  return (
    <div className="flex justify-between gap-3">
      <span>{label}</span>
      <span className="font-semibold text-[#171923]">{value ?? "-"}</span>
    </div>
  );
}

function Indicator({
  label,
  value,
  max,
  tone,
}: {
  label: string;
  value: number;
  max: number;
  tone: "blue" | "green" | "amber";
}) {
  const width = max > 0 ? Math.max(4, Math.min(100, Math.round((value / max) * 100))) : 0;
  const color =
    tone === "blue" ? "bg-[#2563eb]" : tone === "green" ? "bg-[#16a34a]" : "bg-[#d97706]";
  return (
    <div>
      <div className="mb-1 flex justify-between gap-3 text-[11px] text-[#667085]">
        <span>{label}</span>
        <span>{value}</span>
      </div>
      <div className="h-1.5 rounded bg-[#eef2f6]">
        <div className={`h-1.5 rounded ${color}`} style={{ width: `${value > 0 ? width : 0}%` }} />
      </div>
    </div>
  );
}

function withinTimeFilter(run: DiscoveryRunListItem, filter: TimeFilter) {
  if (filter === "all") return true;
  const started = dateMs(run.started_at);
  if (started === null) return false;
  const windowMs = filter === "24h" ? 24 * 60 * 60 * 1000 : 7 * 24 * 60 * 60 * 1000;
  return Date.now() - started <= windowMs;
}

function formatRunDuration(run: DiscoveryRunListItem) {
  const explicit = numberValue(run.duration_ms);
  if (explicit !== null) return formatDuration(explicit);

  const started = dateMs(run.started_at);
  const finished = dateMs(run.finished_at);
  if (started === null || finished === null || finished < started) return "-";
  return formatDuration(finished - started);
}

function warningCount(run: DiscoveryRunListItem) {
  if (Array.isArray(run.warnings)) return run.warnings.length;
  return numberValue(run.warning_count) ?? numberValue(run.warnings_count) ?? 0;
}

function runId(run: DiscoveryRunListItem) {
  return stringValue(run.id) ?? stringValue(run.discovery_run_id);
}

function formatDate(value: unknown) {
  if (typeof value !== "string" || !value.trim()) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString();
}

function stringValue(value: unknown) {
  return typeof value === "string" && value.trim() ? value : null;
}

function numberValue(value: unknown) {
  if (typeof value === "number" && Number.isFinite(value)) return value;
  if (typeof value === "string" && value.trim()) {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : null;
  }
  return null;
}

function dateMs(value: unknown) {
  if (typeof value !== "string" || !value.trim()) return null;
  const parsed = new Date(value).getTime();
  return Number.isNaN(parsed) ? null : parsed;
}
