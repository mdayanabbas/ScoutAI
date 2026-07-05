import type { AgentRun } from "@/types/agent-run";
import {
  EmptyState,
  formatDateTime,
  SectionError,
  SectionShell,
  StatusBadge,
} from "@/components/companies/detail-format";

export function CompanyAgentRuns({
  runs,
  error,
}: {
  runs?: AgentRun[];
  error?: Error | null;
}) {
  return (
    <SectionShell title="Agent Runs">
      {error ? <SectionError message={error.message} /> : null}
      {!error && runs?.length === 0 ? (
        <EmptyState message="No agent runs found." />
      ) : null}
      {!error && runs && runs.length > 0 ? (
        <div className="space-y-3">
          {runs.map((run) => (
            <article
              key={run.id}
              className="rounded-md border border-[#edf0f5] p-4"
            >
              <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
                <div>
                  <h3 className="text-sm font-semibold text-[#171923]">
                    {run.agent_name}
                  </h3>
                  <p className="mt-1 text-sm text-[#667085]">
                    {run.model_provider ?? "No provider"} ·{" "}
                    {run.model_name ?? "No model"}
                  </p>
                </div>
                <StatusBadge value={run.status} />
              </div>
              <div className="mt-3 grid gap-3 text-sm text-[#475467] sm:grid-cols-3">
                <span>Latency: {run.latency_ms ?? "None"} ms</span>
                <span>Created: {formatDateTime(run.created_at)}</span>
                <span>Error: {run.error_message ?? "None"}</span>
              </div>
            </article>
          ))}
        </div>
      ) : null}
    </SectionShell>
  );
}
