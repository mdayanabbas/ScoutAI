"use client";

import {
  EmptyState,
  formatDateTime,
  SectionError,
} from "@/components/companies/detail-format";
import { useAgentRunSteps, useDeleteAgentStep } from "@/hooks/use-agent-runs";

function JsonBlock({ value }: { value: Record<string, unknown> | null }) {
  return (
    <pre className="max-h-48 overflow-auto whitespace-pre-wrap rounded-md border border-[#edf0f5] bg-[#f8fafc] p-3 text-xs leading-5 text-[#475467]">
      {value ? JSON.stringify(value, null, 2) : "None"}
    </pre>
  );
}

export function AgentStepsList({ agentRunId }: { agentRunId: string }) {
  const stepsQuery = useAgentRunSteps(agentRunId);
  const deleteStep = useDeleteAgentStep(agentRunId);

  return (
    <div className="space-y-3">
      {stepsQuery.isLoading ? (
        <div className="h-24 animate-pulse rounded bg-[#eef2f6]" />
      ) : null}
      {stepsQuery.error ? (
        <SectionError
          message={
            stepsQuery.error instanceof Error
              ? stepsQuery.error.message
              : "Steps could not load."
          }
        />
      ) : null}
      {stepsQuery.data?.length === 0 ? (
        <EmptyState message="No agent steps found." />
      ) : null}
      {stepsQuery.data?.map((step) => (
        <article
          key={step.id}
          className="rounded-md border border-[#edf0f5] p-4"
        >
          <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
            <div>
              <h4 className="text-sm font-semibold text-[#171923]">
                {step.step_order ?? "None"} - {step.step_name}
              </h4>
              <p className="mt-1 text-sm text-[#667085]">
                Latency: {step.latency_ms ?? "None"} ms - Created:{" "}
                {formatDateTime(step.created_at)}
              </p>
            </div>
            <button
              type="button"
              onClick={() => deleteStep.mutate(step.id)}
              disabled={deleteStep.isPending}
              className="rounded border border-[#fca5a5] bg-white px-2.5 py-1.5 text-xs font-medium text-[#b42318] hover:bg-[#fff7f7] disabled:cursor-not-allowed disabled:opacity-60"
            >
              {deleteStep.isPending ? "Deleting..." : "Delete"}
            </button>
          </div>
          {step.error_message ? (
            <p className="mt-3 text-sm text-[#b42318]">{step.error_message}</p>
          ) : null}
          <div className="mt-4 grid gap-4 lg:grid-cols-2">
            <div>
              <h5 className="mb-2 text-xs font-semibold uppercase text-[#667085]">
                Input Payload
              </h5>
              <JsonBlock value={step.input_payload} />
            </div>
            <div>
              <h5 className="mb-2 text-xs font-semibold uppercase text-[#667085]">
                Output Payload
              </h5>
              <JsonBlock value={step.output_payload} />
            </div>
          </div>
        </article>
      ))}
    </div>
  );
}
