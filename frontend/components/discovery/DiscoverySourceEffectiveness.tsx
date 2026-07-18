"use client";

import { sourceLabels } from "@/components/discovery/DiscoverySourceSelector";
import { formatDuration } from "@/components/discovery/DiscoveryRunSummary";
import type { SourceEffectivenessSummary } from "@/lib/discovery-effectiveness";

export function DiscoverySourceEffectiveness({
  summary,
}: {
  summary: SourceEffectivenessSummary;
}) {
  const cards = [
    {
      title: "Best Volume Source",
      stat: summary.best_volume_source,
      detail: (source: NonNullable<SourceEffectivenessSummary["best_volume_source"]>) =>
        `${source.total_candidates} candidates, ${source.total_jobs_created + source.total_jobs_existing} jobs`,
    },
    {
      title: "Best Quality Source",
      stat: summary.best_enrichment_source,
      detail: (source: NonNullable<SourceEffectivenessSummary["best_enrichment_source"]>) =>
        source.enrichment_rate === null
          ? "No enrichment rate yet"
          : `${Math.round(source.enrichment_rate * 100)}% enriched`,
    },
    {
      title: "Fastest Source",
      stat: summary.fastest_source,
      detail: (source: NonNullable<SourceEffectivenessSummary["fastest_source"]>) =>
        formatDuration(source.average_duration_ms),
    },
    {
      title: "Needs Attention",
      stat: summary.most_failure_prone_source ?? summary.noisiest_source,
      detail: (source: NonNullable<SourceEffectivenessSummary["most_failure_prone_source"]>) =>
        `${source.failed_runs} failed, ${source.warning_count} warnings`,
    },
  ];

  return (
    <section className="rounded-md border border-[#d9dee8] bg-white p-5">
      <div className="mb-4">
        <h2 className="text-base font-semibold text-[#171923]">Source Comparison</h2>
        <p className="mt-1 text-sm text-[#667085]">
          Lightweight source effectiveness summary from the loaded run history and latest source diagnostics.
        </p>
      </div>

      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
        {cards.map((card) => (
          <div key={card.title} className="rounded border border-[#e4e7ec] bg-[#fcfcfd] p-3">
            <p className="text-xs font-medium uppercase tracking-normal text-[#667085]">{card.title}</p>
            {card.stat ? (
              <>
                <p className="mt-1 text-lg font-semibold text-[#171923]">
                  {sourceLabels[card.stat.source] ?? card.stat.source}
                </p>
                <p className="mt-1 text-sm text-[#667085]">{card.detail(card.stat)}</p>
              </>
            ) : (
              <p className="mt-2 text-sm text-[#667085]">Not enough data yet</p>
            )}
          </div>
        ))}
      </div>

      {summary.sources.length ? (
        <div className="mt-4 overflow-x-auto">
          <table className="min-w-full text-left text-sm">
            <thead className="border-b border-[#e4e7ec] text-xs uppercase tracking-normal text-[#667085]">
              <tr>
                <th className="py-2 pr-4 font-semibold">Source</th>
                <th className="py-2 pr-4 font-semibold">Runs</th>
                <th className="py-2 pr-4 font-semibold">Jobs Scored</th>
                <th className="py-2 pr-4 font-semibold">Failure Rate</th>
                <th className="py-2 pr-4 font-semibold">Warnings</th>
                <th className="py-2 pr-4 font-semibold">Avg Duration</th>
              </tr>
            </thead>
            <tbody>
              {summary.sources.map((source) => (
                <tr key={source.source} className="border-b border-[#f2f4f7] last:border-0">
                  <td className="py-2 pr-4 font-medium text-[#171923]">
                    {sourceLabels[source.source] ?? source.source}
                  </td>
                  <td className="py-2 pr-4 text-[#475467]">{source.total_runs}</td>
                  <td className="py-2 pr-4 text-[#475467]">{source.total_jobs_scored}</td>
                  <td className="py-2 pr-4 text-[#475467]">
                    {Math.round(source.failure_rate * 100)}%
                  </td>
                  <td className="py-2 pr-4 text-[#475467]">{source.warning_count}</td>
                  <td className="py-2 pr-4 text-[#475467]">
                    {formatDuration(source.average_duration_ms)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <p className="mt-4 text-sm text-[#667085]">Not enough data yet.</p>
      )}
    </section>
  );
}
