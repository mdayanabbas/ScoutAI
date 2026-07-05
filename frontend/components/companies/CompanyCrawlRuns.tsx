import type { CrawlRun } from "@/types/crawl-run";
import {
  EmptyState,
  formatDateTime,
  formatNumber,
  SectionError,
  SectionShell,
  StatusBadge,
} from "@/components/companies/detail-format";

export function CompanyCrawlRuns({
  runs,
  error,
}: {
  runs?: CrawlRun[];
  error?: Error | null;
}) {
  return (
    <SectionShell title="Crawl Runs">
      {error ? <SectionError message={error.message} /> : null}
      {!error && runs?.length === 0 ? (
        <EmptyState message="No crawl runs found." />
      ) : null}
      {!error && runs && runs.length > 0 ? (
        <div className="space-y-3">
          {runs.map((run) => (
            <article
              key={run.id}
              className="rounded-md border border-[#edf0f5] p-4"
            >
              <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                <StatusBadge value={run.status} />
                <span className="text-sm text-[#667085]">
                  {formatDateTime(run.started_at)}
                </span>
              </div>
              <div className="mt-3 grid gap-3 text-sm text-[#475467] sm:grid-cols-2 lg:grid-cols-4">
                <span>Finished: {formatDateTime(run.finished_at)}</span>
                <span>Pages found: {formatNumber(run.pages_found)}</span>
                <span>Pages crawled: {formatNumber(run.pages_crawled)}</span>
                <span>Error: {run.error_message ?? "None"}</span>
              </div>
            </article>
          ))}
        </div>
      ) : null}
    </SectionShell>
  );
}
