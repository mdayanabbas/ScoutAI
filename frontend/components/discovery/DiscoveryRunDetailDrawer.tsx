"use client";

import { useState } from "react";

import { StatusBadge, formatDuration } from "@/components/discovery/DiscoveryRunSummary";
import { normalizeDiscoveryRunDetail } from "@/lib/discovery-run-normalization";

const detailFields = [
  ["source", "Source"],
  ["status", "Status"],
  ["startedAt", "Started"],
  ["finishedAt", "Finished"],
  ["durationMs", "Duration"],
  ["candidatesFound", "Candidates Found"],
  ["candidatesNormalized", "Candidates Normalized"],
  ["candidatesDeferred", "Candidates Deferred"],
  ["candidatesRejected", "Candidates Rejected"],
  ["candidatesFailed", "Candidates Failed"],
  ["companiesCreated", "Companies Created"],
  ["companiesMatched", "Companies Matched"],
  ["domainsResolved", "Domains Resolved"],
  ["domainsUnresolved", "Domains Unresolved"],
  ["jobsCreated", "Jobs Created"],
  ["jobsExisting", "Jobs Existing"],
  ["jobsUpdated", "Jobs Updated"],
  ["jobsSkipped", "Jobs Skipped"],
  ["jobsEnriched", "Jobs Enriched"],
  ["jobsScored", "Jobs Scored"],
  ["jobsFailed", "Jobs Failed"],
  ["error_message", "Error"],
] as const;

export function DiscoveryRunDetailDrawer({
  run,
  loadingRunId,
  error,
  onClose,
}: {
  run: Record<string, unknown> | null;
  loadingRunId: string | null;
  error: string | null;
  onClose: () => void;
}) {
  const [showRaw, setShowRaw] = useState(false);
  if (!run && !loadingRunId && !error) return null;

  const detail = normalizeDiscoveryRunDetail(run, loadingRunId);
  const hasMetadata = Object.keys(detail.metadata).length > 0;
  const hasDiagnostics = Object.keys(detail.diagnostics).length > 0;

  return (
    <div className="fixed inset-0 z-40 bg-[#101828]/30">
      <div className="absolute right-0 top-0 h-full w-full max-w-2xl overflow-y-auto bg-white p-5 shadow-xl">
        <div className="mb-5 flex items-start justify-between gap-4">
          <div>
            <h2 className="text-lg font-semibold text-[#171923]">Discovery Run Details</h2>
            <p className="mt-1 font-mono text-xs text-[#667085]">
              {detail.id ?? "Selected run"}
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded border border-[#c8ced8] px-3 py-2 text-sm font-medium text-[#344054] hover:bg-[#f8fafc]"
          >
            Close
          </button>
        </div>

        {loadingRunId && !run && !error ? (
          <p className="text-sm text-[#667085]">Loading run details...</p>
        ) : null}
        {error ? (
          <div className="rounded border border-[#fecaca] bg-[#fff7f7] p-3 text-sm text-[#991b1b]">
            {error}
          </div>
        ) : null}

        {run ? (
          <div className="space-y-5">
            <div className="flex flex-wrap items-center gap-2">
              <StatusBadge status={detail.status} />
              <span className="rounded border border-[#e4e7ec] px-2.5 py-1 text-xs font-medium text-[#475467]">
                {detail.durationMs === null ? "—" : formatDuration(detail.durationMs)}
              </span>
            </div>
            {!detail.sourceMapped ? (
              <div className="rounded border border-[#fedf89] bg-[#fffbeb] p-3 text-sm text-[#92400e]">
                Source could not be mapped from this response.
              </div>
            ) : null}

            <div className="grid gap-3 sm:grid-cols-2">
              {detailFields.map(([key, label]) => (
                <div key={key} className="rounded border border-[#e4e7ec] bg-[#fcfcfd] p-3">
                  <p className="text-xs font-medium uppercase tracking-normal text-[#667085]">{label}</p>
                  <p className="mt-1 break-words text-sm font-semibold text-[#171923]">
                    {detailValue(detail, key)}
                  </p>
                </div>
              ))}
            </div>

            <section className="rounded border border-[#e4e7ec] bg-[#fcfcfd] p-3">
              <h3 className="text-sm font-semibold text-[#344054]">Metadata</h3>
              {hasMetadata ? (
                <pre className="mt-3 max-h-48 overflow-auto rounded bg-[#101828] p-3 text-xs leading-5 text-white">
                  {JSON.stringify(detail.metadata, null, 2)}
                </pre>
              ) : (
                <p className="mt-2 text-sm text-[#667085]">No metadata returned for this run.</p>
              )}
            </section>

            <section className="rounded border border-[#e4e7ec] bg-[#fcfcfd] p-3">
              <h3 className="text-sm font-semibold text-[#344054]">Diagnostics</h3>
              {hasDiagnostics ? (
                <pre className="mt-3 max-h-48 overflow-auto rounded bg-[#101828] p-3 text-xs leading-5 text-white">
                  {JSON.stringify(detail.diagnostics, null, 2)}
                </pre>
              ) : (
                <p className="mt-2 text-sm text-[#667085]">No diagnostics returned for this run.</p>
              )}
            </section>

            <section className="rounded border border-[#fedf89] bg-[#fffbeb] p-3">
              <h3 className="text-sm font-semibold text-[#92400e]">Warnings</h3>
              {detail.warnings.length ? (
                <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-[#92400e]">
                  {detail.warnings.map((warning, index) => (
                    <li key={`${String(warning)}-${index}`}>{String(warning)}</li>
                  ))}
                </ul>
              ) : (
                <p className="mt-2 text-sm text-[#92400e]">No warnings recorded.</p>
              )}
            </section>

            <button
              type="button"
              onClick={() => setShowRaw((value) => !value)}
              className="rounded border border-[#c8ced8] px-3 py-2 text-sm font-medium text-[#344054] hover:bg-[#f8fafc]"
            >
              {showRaw ? "Hide Raw JSON" : "Show Raw JSON"}
            </button>

            {showRaw ? (
              <pre className="max-h-96 overflow-auto rounded bg-[#101828] p-4 text-xs leading-5 text-white">
                {JSON.stringify(detail.raw, null, 2)}
              </pre>
            ) : null}
          </div>
        ) : null}
      </div>
    </div>
  );
}

function detailValue(detail: ReturnType<typeof normalizeDiscoveryRunDetail>, key: string) {
  if (key === "durationMs") return detail.durationMs === null ? "—" : formatDuration(detail.durationMs);
  if (key === "error_message") return detail.error ?? "—";
  const value = detail[key as keyof typeof detail];
  if (key === "startedAt" || key === "finishedAt") return formatDate(value);
  if (value === null || value === undefined || value === "") return "—";
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

function formatDate(value: unknown) {
  if (typeof value !== "string" || !value.trim()) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString();
}
