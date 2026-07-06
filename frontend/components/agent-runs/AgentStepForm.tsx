"use client";

import { FormEvent, ReactNode, useState } from "react";

import { ApiError } from "@/lib/api";
import type { AgentStepCreateInput } from "@/types/agent-run";

type AgentStepFormProps = {
  isSubmitting?: boolean;
  submitError?: unknown;
  onSubmit: (data: AgentStepCreateInput) => Promise<void> | void;
  onCancel?: () => void;
};

function optionalText(value: string) {
  const trimmed = value.trim();
  return trimmed === "" ? null : trimmed;
}

function optionalNumber(value: string) {
  if (value.trim() === "") {
    return null;
  }
  return Number(value);
}

function parseOptionalJson(value: string, label: string) {
  if (!value.trim()) {
    return null;
  }
  try {
    return JSON.parse(value) as Record<string, unknown>;
  } catch {
    throw new Error(`${label} must be valid JSON.`);
  }
}

function errorMessage(error: unknown) {
  if (error instanceof ApiError || error instanceof Error) {
    return error.message;
  }
  return null;
}

export function AgentStepForm({
  isSubmitting = false,
  submitError,
  onSubmit,
  onCancel,
}: AgentStepFormProps) {
  const [stepName, setStepName] = useState("");
  const [stepOrder, setStepOrder] = useState("");
  const [inputPayloadText, setInputPayloadText] = useState("");
  const [outputPayloadText, setOutputPayloadText] = useState("");
  const [errorMessageText, setErrorMessageText] = useState("");
  const [latencyMs, setLatencyMs] = useState("");
  const [validationError, setValidationError] = useState<string | null>(null);
  const backendError = errorMessage(submitError);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const order = Number(stepOrder);
    const latency = optionalNumber(latencyMs);

    if (!stepName.trim()) {
      setValidationError("Step name is required.");
      return;
    }
    if (!Number.isInteger(order) || order < 0) {
      setValidationError("Step order must be a whole number greater than or equal to 0.");
      return;
    }
    if (latency !== null && (!Number.isInteger(latency) || latency < 0)) {
      setValidationError("Latency must be a whole number greater than or equal to 0.");
      return;
    }

    try {
      const inputPayload = parseOptionalJson(inputPayloadText, "Input payload");
      const outputPayload = parseOptionalJson(outputPayloadText, "Output payload");
      setValidationError(null);
      await onSubmit({
        step_name: stepName.trim(),
        step_order: order,
        input_payload: inputPayload,
        output_payload: outputPayload,
        error_message: optionalText(errorMessageText),
        latency_ms: latency,
      });
      setStepName("");
      setStepOrder("");
      setInputPayloadText("");
      setOutputPayloadText("");
      setErrorMessageText("");
      setLatencyMs("");
    } catch (error) {
      setValidationError(error instanceof Error ? error.message : "Invalid step data.");
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-5">
      {validationError || backendError ? (
        <div className="rounded-md border border-[#fecaca] bg-[#fff7f7] p-3 text-sm text-[#991b1b]">
          {validationError ?? backendError}
        </div>
      ) : null}

      <div className="grid gap-4 sm:grid-cols-2">
        <Field label="Step Name">
          <input
            value={stepName}
            onChange={(event) => setStepName(event.target.value)}
            className="w-full rounded border border-[#c8ced8] px-3 py-2 text-sm outline-none focus:border-[#172033]"
          />
        </Field>
        <Field label="Step Order">
          <input
            type="number"
            min={0}
            value={stepOrder}
            onChange={(event) => setStepOrder(event.target.value)}
            className="w-full rounded border border-[#c8ced8] px-3 py-2 text-sm outline-none focus:border-[#172033]"
          />
        </Field>
      </div>

      <Field label="Input Payload JSON">
        <textarea
          value={inputPayloadText}
          onChange={(event) => setInputPayloadText(event.target.value)}
          className="min-h-24 w-full rounded border border-[#c8ced8] px-3 py-2 font-mono text-xs outline-none focus:border-[#172033]"
        />
      </Field>

      <Field label="Output Payload JSON">
        <textarea
          value={outputPayloadText}
          onChange={(event) => setOutputPayloadText(event.target.value)}
          className="min-h-24 w-full rounded border border-[#c8ced8] px-3 py-2 font-mono text-xs outline-none focus:border-[#172033]"
        />
      </Field>

      <div className="grid gap-4 sm:grid-cols-2">
        <Field label="Error Message">
          <input
            value={errorMessageText}
            onChange={(event) => setErrorMessageText(event.target.value)}
            className="w-full rounded border border-[#c8ced8] px-3 py-2 text-sm outline-none focus:border-[#172033]"
          />
        </Field>
        <Field label="Latency ms">
          <input
            type="number"
            min={0}
            value={latencyMs}
            onChange={(event) => setLatencyMs(event.target.value)}
            className="w-full rounded border border-[#c8ced8] px-3 py-2 text-sm outline-none focus:border-[#172033]"
          />
        </Field>
      </div>

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
          {isSubmitting ? "Adding..." : "Add Step"}
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
