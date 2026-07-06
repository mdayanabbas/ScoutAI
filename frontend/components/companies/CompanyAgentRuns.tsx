"use client";

import { FormEvent, useState, type ReactNode } from "react";

import { AgentRunForm } from "@/components/agent-runs/AgentRunForm";
import { AgentStepForm } from "@/components/agent-runs/AgentStepForm";
import { AgentStepsList } from "@/components/agent-runs/AgentStepsList";
import {
  EmptyState,
  formatDateTime,
  SectionError,
  SectionShell,
  StatusBadge,
} from "@/components/companies/detail-format";
import {
  useAgentRun,
  useCreateAgentRun,
  useCreateAgentRunStep,
  useMarkAgentRunFailed,
  useMarkAgentRunRunning,
  useMarkAgentRunSuccess,
} from "@/hooks/use-agent-runs";
import type {
  AgentRun,
  AgentRunCreateInput,
  AgentRunMarkFailedInput,
  AgentRunMarkSuccessInput,
  AgentStepCreateInput,
} from "@/types/agent-run";

export function CompanyAgentRuns({
  companyId,
  runs,
  isLoading = false,
  error,
}: {
  companyId: string;
  runs?: AgentRun[];
  isLoading?: boolean;
  error?: Error | null;
}) {
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [viewingRunId, setViewingRunId] = useState<string | null>(null);
  const [successRun, setSuccessRun] = useState<AgentRun | null>(null);
  const [failedRun, setFailedRun] = useState<AgentRun | null>(null);
  const [stepRun, setStepRun] = useState<AgentRun | null>(null);
  const createRun = useCreateAgentRun(companyId);
  const markRunning = useMarkAgentRunRunning(companyId);
  const markSuccess = useMarkAgentRunSuccess(companyId);
  const markFailed = useMarkAgentRunFailed(companyId);
  const runDetail = useAgentRun(viewingRunId);

  async function handleCreateRun(input: AgentRunCreateInput) {
    await createRun.mutateAsync(input);
    setIsCreateOpen(false);
  }

  async function handleMarkRunning(agentRunId: string) {
    await markRunning.mutateAsync(agentRunId);
  }

  async function handleMarkSuccess(data: AgentRunMarkSuccessInput) {
    if (!successRun) {
      return;
    }

    await markSuccess.mutateAsync({ agentRunId: successRun.id, data });
    setSuccessRun(null);
  }

  async function handleMarkFailed(data: AgentRunMarkFailedInput) {
    if (!failedRun) {
      return;
    }

    await markFailed.mutateAsync({ agentRunId: failedRun.id, data });
    setFailedRun(null);
  }

  return (
    <SectionShell title="Agent Runs">
      <div className="mb-4 flex items-center justify-between gap-3">
        <p className="text-sm text-[#667085]">
          Create and update manual agent run tracking records. No LLM calls are
          executed here.
        </p>
        <button
          type="button"
          onClick={() => {
            createRun.reset();
            setIsCreateOpen(true);
          }}
          className="rounded bg-[#172033] px-3 py-2 text-sm font-medium text-white hover:bg-[#24314a]"
        >
          Create Agent Run
        </button>
      </div>

      {isLoading ? (
        <div className="space-y-3">
          {Array.from({ length: 3 }).map((_, index) => (
            <div
              key={index}
              className="h-24 animate-pulse rounded bg-[#eef2f6]"
            />
          ))}
        </div>
      ) : null}

      {error ? <SectionError message={error.message} /> : null}
      {!isLoading && !error && runs?.length === 0 ? (
        <EmptyState message="No agent runs found." />
      ) : null}
      {!isLoading && !error && runs && runs.length > 0 ? (
        <div className="space-y-3">
          {runs.map((run) => {
            const canMarkRunning = run.status === "pending";
            const canComplete =
              run.status === "pending" || run.status === "running";

            return (
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
                      {run.model_provider ?? "No provider"} -{" "}
                      {run.model_name ?? "No model"}
                    </p>
                  </div>
                  <StatusBadge value={run.status} />
                </div>
                <div className="mt-3 grid gap-3 text-sm text-[#475467] sm:grid-cols-2 lg:grid-cols-4">
                  <span>Latency: {run.latency_ms ?? "None"} ms</span>
                  <span>Created: {formatDateTime(run.created_at)}</span>
                  <span>Input: {run.input_summary ?? "None"}</span>
                  <span>Output: {run.output_summary ?? "None"}</span>
                  <span className="lg:col-span-4">
                    Error: {run.error_message ?? "None"}
                  </span>
                </div>
                <div className="mt-4 flex flex-wrap justify-end gap-2">
                  <button
                    type="button"
                    onClick={() => setViewingRunId(run.id)}
                    className="rounded border border-[#c8ced8] bg-white px-2.5 py-1.5 text-xs font-medium text-[#344054] hover:bg-[#f8fafc]"
                  >
                    View
                  </button>
                  <button
                    type="button"
                    onClick={() => setStepRun(run)}
                    className="rounded border border-[#c8ced8] bg-white px-2.5 py-1.5 text-xs font-medium text-[#344054] hover:bg-[#f8fafc]"
                  >
                    Add Step
                  </button>
                  {canMarkRunning ? (
                    <button
                      type="button"
                      onClick={() => handleMarkRunning(run.id)}
                      disabled={markRunning.isPending}
                      className="rounded border border-[#c8ced8] bg-white px-2.5 py-1.5 text-xs font-medium text-[#344054] hover:bg-[#f8fafc] disabled:cursor-not-allowed disabled:opacity-60"
                    >
                      {markRunning.isPending ? "Updating..." : "Mark Running"}
                    </button>
                  ) : null}
                  {canComplete ? (
                    <>
                      <button
                        type="button"
                        onClick={() => {
                          markSuccess.reset();
                          setSuccessRun(run);
                        }}
                        className="rounded border border-[#86efac] bg-white px-2.5 py-1.5 text-xs font-medium text-[#166534] hover:bg-[#f0fdf4]"
                      >
                        Mark Success
                      </button>
                      <button
                        type="button"
                        onClick={() => {
                          markFailed.reset();
                          setFailedRun(run);
                        }}
                        className="rounded border border-[#fca5a5] bg-white px-2.5 py-1.5 text-xs font-medium text-[#b42318] hover:bg-[#fff7f7]"
                      >
                        Mark Failed
                      </button>
                    </>
                  ) : null}
                </div>
              </article>
            );
          })}
        </div>
      ) : null}

      {isCreateOpen ? (
        <Modal title="Create Agent Run" onClose={() => setIsCreateOpen(false)}>
          <AgentRunForm
            isSubmitting={createRun.isPending}
            submitError={createRun.error}
            onSubmit={handleCreateRun}
            onCancel={() => setIsCreateOpen(false)}
          />
        </Modal>
      ) : null}

      {viewingRunId ? (
        <Modal title="Agent Run Details" onClose={() => setViewingRunId(null)}>
          {runDetail.isLoading ? (
            <div className="h-24 animate-pulse rounded bg-[#eef2f6]" />
          ) : null}
          {runDetail.error ? (
            <SectionError
              message={
                runDetail.error instanceof Error
                  ? runDetail.error.message
                  : "Agent run could not load."
              }
            />
          ) : null}
          {runDetail.data ? <AgentRunDetails run={runDetail.data} /> : null}
          <div className="mt-5">
            <h4 className="mb-3 text-sm font-semibold text-[#171923]">Steps</h4>
            <AgentStepsList agentRunId={viewingRunId} />
          </div>
        </Modal>
      ) : null}

      {stepRun ? (
        <Modal title="Add Agent Step" onClose={() => setStepRun(null)}>
          <CreateStepPanel
            agentRunId={stepRun.id}
            onClose={() => setStepRun(null)}
          />
        </Modal>
      ) : null}

      {successRun ? (
        <Modal title="Mark Agent Run Success" onClose={() => setSuccessRun(null)}>
          <MarkSuccessForm
            isSubmitting={markSuccess.isPending}
            submitError={markSuccess.error}
            onSubmit={handleMarkSuccess}
            onCancel={() => setSuccessRun(null)}
          />
        </Modal>
      ) : null}

      {failedRun ? (
        <Modal title="Mark Agent Run Failed" onClose={() => setFailedRun(null)}>
          <MarkFailedForm
            isSubmitting={markFailed.isPending}
            submitError={markFailed.error}
            onSubmit={handleMarkFailed}
            onCancel={() => setFailedRun(null)}
          />
        </Modal>
      ) : null}
    </SectionShell>
  );
}

function CreateStepPanel({
  agentRunId,
  onClose,
}: {
  agentRunId: string;
  onClose: () => void;
}) {
  const createStep = useCreateAgentRunStep(agentRunId);

  async function handleSubmit(data: AgentStepCreateInput) {
    await createStep.mutateAsync(data);
    onClose();
  }

  return (
    <AgentStepForm
      isSubmitting={createStep.isPending}
      submitError={createStep.error}
      onSubmit={handleSubmit}
      onCancel={onClose}
    />
  );
}

function Modal({
  title,
  children,
  onClose,
}: {
  title: string;
  children: ReactNode;
  onClose: () => void;
}) {
  return (
    <div className="fixed inset-0 z-50 overflow-y-auto bg-[#101828]/40 px-4 py-6 sm:py-10">
      <div className="mx-auto max-w-4xl rounded-md bg-white shadow-xl">
        <div className="flex items-start justify-between gap-4 border-b border-[#edf0f5] px-5 py-4">
          <h3 className="text-lg font-semibold text-[#171923]">{title}</h3>
          <button
            type="button"
            onClick={onClose}
            className="rounded border border-[#c8ced8] px-2.5 py-1.5 text-sm text-[#475467] hover:bg-[#f8fafc]"
          >
            Close
          </button>
        </div>
        <div className="px-5 py-5">{children}</div>
      </div>
    </div>
  );
}

function AgentRunDetails({ run }: { run: AgentRun }) {
  return (
    <div className="space-y-4">
      <div className="grid gap-4 sm:grid-cols-2">
        <DetailItem label="ID" value={run.id} />
        <DetailItem label="Company ID" value={run.company_id ?? "None"} />
        <DetailItem label="Job ID" value={run.job_id ?? "None"} />
        <DetailItem label="Agent" value={run.agent_name} />
        <DetailItem label="Status" value={run.status} />
        <DetailItem label="Provider" value={run.model_provider ?? "None"} />
        <DetailItem label="Model" value={run.model_name ?? "None"} />
        <DetailItem label="Latency" value={`${run.latency_ms ?? "None"} ms`} />
        <DetailItem label="Started" value={formatDateTime(run.started_at)} />
        <DetailItem label="Finished" value={formatDateTime(run.finished_at)} />
        <DetailItem label="Created" value={formatDateTime(run.created_at)} />
        <DetailItem label="Updated" value={formatDateTime(run.updated_at)} />
      </div>
      <TextBlock label="Input Summary" value={run.input_summary} />
      <TextBlock label="Output Summary" value={run.output_summary} />
      <TextBlock label="Error Message" value={run.error_message} />
      <TextBlock
        label="Metadata"
        value={run.metadata ? JSON.stringify(run.metadata, null, 2) : null}
        mono
      />
    </div>
  );
}

function MarkSuccessForm({
  isSubmitting,
  submitError,
  onSubmit,
  onCancel,
}: {
  isSubmitting: boolean;
  submitError: unknown;
  onSubmit: (data: AgentRunMarkSuccessInput) => Promise<void> | void;
  onCancel: () => void;
}) {
  const [outputSummary, setOutputSummary] = useState("");
  const [latencyMs, setLatencyMs] = useState("");
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const latency = latencyMs.trim() === "" ? null : Number(latencyMs);
    if (latency !== null && (!Number.isInteger(latency) || latency < 0)) {
      setError("Latency must be a whole number greater than or equal to 0.");
      return;
    }
    setError(null);
    await onSubmit({
      output_summary: outputSummary.trim() || null,
      latency_ms: latency,
    });
  }

  return (
    <StatusFormShell
      error={error}
      submitError={submitError}
      submitLabel="Mark Success"
      isSubmitting={isSubmitting}
      onCancel={onCancel}
      onSubmit={handleSubmit}
    >
      <TextAreaField
        label="Output Summary"
        value={outputSummary}
        onChange={setOutputSummary}
      />
      <NumberField label="Latency ms" value={latencyMs} onChange={setLatencyMs} />
    </StatusFormShell>
  );
}

function MarkFailedForm({
  isSubmitting,
  submitError,
  onSubmit,
  onCancel,
}: {
  isSubmitting: boolean;
  submitError: unknown;
  onSubmit: (data: AgentRunMarkFailedInput) => Promise<void> | void;
  onCancel: () => void;
}) {
  const [errorMessage, setErrorMessage] = useState("");
  const [latencyMs, setLatencyMs] = useState("");
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const latency = latencyMs.trim() === "" ? null : Number(latencyMs);
    if (!errorMessage.trim()) {
      setError("Error message is required.");
      return;
    }
    if (latency !== null && (!Number.isInteger(latency) || latency < 0)) {
      setError("Latency must be a whole number greater than or equal to 0.");
      return;
    }
    setError(null);
    await onSubmit({ error_message: errorMessage.trim(), latency_ms: latency });
  }

  return (
    <StatusFormShell
      error={error}
      submitError={submitError}
      submitLabel="Mark Failed"
      isSubmitting={isSubmitting}
      onCancel={onCancel}
      onSubmit={handleSubmit}
      destructive
    >
      <TextAreaField
        label="Error Message"
        value={errorMessage}
        onChange={setErrorMessage}
      />
      <NumberField label="Latency ms" value={latencyMs} onChange={setLatencyMs} />
    </StatusFormShell>
  );
}

function StatusFormShell({
  children,
  error,
  submitError,
  submitLabel,
  isSubmitting,
  onCancel,
  onSubmit,
  destructive = false,
}: {
  children: ReactNode;
  error: string | null;
  submitError: unknown;
  submitLabel: string;
  isSubmitting: boolean;
  onCancel: () => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
  destructive?: boolean;
}) {
  return (
    <form onSubmit={onSubmit} className="space-y-4">
      {error || submitError ? (
        <SectionError
          message={
            error ??
            (submitError instanceof Error
              ? submitError.message
              : "Agent run could not be updated.")
          }
        />
      ) : null}
      {children}
      <div className="flex justify-end gap-3 border-t border-[#edf0f5] pt-4">
        <button
          type="button"
          onClick={onCancel}
          disabled={isSubmitting}
          className="rounded border border-[#c8ced8] bg-white px-4 py-2 text-sm font-medium text-[#344054] hover:bg-[#f8fafc] disabled:cursor-not-allowed disabled:opacity-60"
        >
          Cancel
        </button>
        <button
          type="submit"
          disabled={isSubmitting}
          className={[
            "rounded px-4 py-2 text-sm font-medium text-white disabled:cursor-not-allowed disabled:opacity-60",
            destructive
              ? "bg-[#b42318] hover:bg-[#991b1b]"
              : "bg-[#172033] hover:bg-[#24314a]",
          ].join(" ")}
        >
          {isSubmitting ? "Saving..." : submitLabel}
        </button>
      </div>
    </form>
  );
}

function TextAreaField({
  label,
  value,
  onChange,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
}) {
  return (
    <label className="block">
      <span className="mb-1.5 block text-sm font-medium text-[#344054]">
        {label}
      </span>
      <textarea
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="min-h-24 w-full rounded border border-[#c8ced8] px-3 py-2 text-sm outline-none focus:border-[#172033]"
      />
    </label>
  );
}

function NumberField({
  label,
  value,
  onChange,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
}) {
  return (
    <label className="block">
      <span className="mb-1.5 block text-sm font-medium text-[#344054]">
        {label}
      </span>
      <input
        type="number"
        min={0}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="w-full rounded border border-[#c8ced8] px-3 py-2 text-sm outline-none focus:border-[#172033]"
      />
    </label>
  );
}

function TextBlock({
  label,
  value,
  mono = false,
}: {
  label: string;
  value: string | null;
  mono?: boolean;
}) {
  return (
    <div>
      <h4 className="text-sm font-semibold text-[#171923]">{label}</h4>
      <div
        className={[
          "mt-2 max-h-80 overflow-auto whitespace-pre-wrap rounded-md border border-[#edf0f5] bg-[#f8fafc] p-3 text-sm leading-6 text-[#475467]",
          mono ? "font-mono text-xs" : "",
        ].join(" ")}
      >
        {value ?? "None"}
      </div>
    </div>
  );
}

function DetailItem({
  label,
  value,
}: {
  label: string;
  value: string | number;
}) {
  return (
    <div>
      <dt className="text-xs font-medium uppercase text-[#667085]">{label}</dt>
      <dd className="mt-1 break-words text-sm text-[#171923]">{value}</dd>
    </div>
  );
}
