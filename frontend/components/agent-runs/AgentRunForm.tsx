"use client";

import { FormEvent, ReactNode, useState } from "react";

import { ApiError } from "@/lib/api";
import type { AgentRunCreateInput } from "@/types/agent-run";

const agentNameOptions = [
  "job_understanding_agent",
  "company_research_agent",
  "funding_agent",
  "founder_signal_agent",
  "tech_stack_agent",
  "outreach_agent",
  "manual_test_agent",
];

type AgentRunFormProps = {
  isSubmitting?: boolean;
  submitError?: unknown;
  onSubmit: (data: AgentRunCreateInput) => Promise<void> | void;
  onCancel?: () => void;
};

function optionalText(value: string) {
  const trimmed = value.trim();
  return trimmed === "" ? null : trimmed;
}

function errorMessage(error: unknown) {
  if (error instanceof ApiError || error instanceof Error) {
    return error.message;
  }
  return null;
}

export function AgentRunForm({
  isSubmitting = false,
  submitError,
  onSubmit,
  onCancel,
}: AgentRunFormProps) {
  const [agentName, setAgentName] = useState("job_understanding_agent");
  const [modelProvider, setModelProvider] = useState("manual");
  const [modelName, setModelName] = useState("test-model");
  const [inputSummary, setInputSummary] = useState("");
  const [metadataSource, setMetadataSource] = useState("");
  const [validationError, setValidationError] = useState<string | null>(null);
  const backendError = errorMessage(submitError);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!agentName.trim()) {
      setValidationError("Agent name is required.");
      return;
    }

    setValidationError(null);
    await onSubmit({
      agent_name: agentName,
      model_provider: optionalText(modelProvider),
      model_name: optionalText(modelName),
      input_summary: optionalText(inputSummary),
      metadata: metadataSource.trim()
        ? { source: metadataSource.trim() }
        : null,
    });

    setAgentName("job_understanding_agent");
    setModelProvider("manual");
    setModelName("test-model");
    setInputSummary("");
    setMetadataSource("");
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-5">
      {validationError || backendError ? (
        <div className="rounded-md border border-[#fecaca] bg-[#fff7f7] p-3 text-sm text-[#991b1b]">
          {validationError ?? backendError}
        </div>
      ) : null}

      <Field label="Agent Name">
        <select
          value={agentName}
          onChange={(event) => setAgentName(event.target.value)}
          className="w-full rounded border border-[#c8ced8] px-3 py-2 text-sm outline-none focus:border-[#172033]"
        >
          {agentNameOptions.map((option) => (
            <option key={option} value={option}>
              {option}
            </option>
          ))}
        </select>
      </Field>

      <div className="grid gap-4 sm:grid-cols-2">
        <Field label="Model Provider">
          <input
            value={modelProvider}
            onChange={(event) => setModelProvider(event.target.value)}
            className="w-full rounded border border-[#c8ced8] px-3 py-2 text-sm outline-none focus:border-[#172033]"
          />
        </Field>
        <Field label="Model Name">
          <input
            value={modelName}
            onChange={(event) => setModelName(event.target.value)}
            className="w-full rounded border border-[#c8ced8] px-3 py-2 text-sm outline-none focus:border-[#172033]"
          />
        </Field>
      </div>

      <Field label="Input Summary">
        <textarea
          value={inputSummary}
          onChange={(event) => setInputSummary(event.target.value)}
          className="min-h-24 w-full rounded border border-[#c8ced8] px-3 py-2 text-sm outline-none focus:border-[#172033]"
        />
      </Field>

      <Field label="Metadata Source">
        <input
          value={metadataSource}
          onChange={(event) => setMetadataSource(event.target.value)}
          className="w-full rounded border border-[#c8ced8] px-3 py-2 text-sm outline-none focus:border-[#172033]"
          placeholder="manual_test"
        />
      </Field>

      <div className="flex justify-end gap-3 border-t border-[#edf0f5] pt-5">
        {onCancel ? (
          <button
            type="button"
            onClick={onCancel}
            className="rounded border border-[#c8ced8] bg-white px-4 py-2 text-sm font-medium text-[#344054] hover:bg-[#f8fafc]"
          >
            Cancel
          </button>
        ) : null}
        <button
          type="submit"
          disabled={isSubmitting}
          className="rounded bg-[#172033] px-4 py-2 text-sm font-medium text-white disabled:cursor-not-allowed disabled:opacity-60"
        >
          {isSubmitting ? "Creating..." : "Create Agent Run"}
        </button>
      </div>
    </form>
  );
}

function Field({
  label,
  children,
}: {
  label: string;
  children: ReactNode;
}) {
  return (
    <label className="block">
      <span className="mb-1.5 block text-sm font-medium text-[#344054]">
        {label}
      </span>
      {children}
    </label>
  );
}
