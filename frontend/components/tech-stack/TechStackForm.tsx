"use client";

import { FormEvent, ReactNode, useEffect, useMemo, useState } from "react";

import { ApiError } from "@/lib/api";
import type {
  TechStackCategory,
  TechStackItem,
  TechStackItemCreateInput,
  TechStackSource,
} from "@/types/tech-stack";

const categoryOptions: Array<{ value: TechStackCategory; label: string }> = [
  { value: "programming_language", label: "Programming Language" },
  { value: "backend_framework", label: "Backend Framework" },
  { value: "frontend_framework", label: "Frontend Framework" },
  { value: "database", label: "Database" },
  { value: "cloud", label: "Cloud" },
  { value: "infrastructure", label: "Infrastructure" },
  { value: "devops", label: "DevOps" },
  { value: "ai_ml", label: "AI / ML" },
  { value: "vector_database", label: "Vector Database" },
  { value: "monitoring", label: "Monitoring" },
  { value: "testing", label: "Testing" },
  { value: "other", label: "Other" },
];

const sourceOptions: Array<{ value: TechStackSource; label: string }> = [
  { value: "manual", label: "Manual" },
  { value: "job_description", label: "Job Description" },
  { value: "company_website", label: "Company Website" },
  { value: "careers_page", label: "Careers Page" },
  { value: "engineering_blog", label: "Engineering Blog" },
  { value: "github", label: "GitHub" },
  { value: "agent", label: "Agent" },
  { value: "other", label: "Other" },
];

type TechStackFormValues = {
  name: string;
  category: TechStackCategory;
  source: TechStackSource;
  confidence: string;
};

const emptyValues: TechStackFormValues = {
  name: "",
  category: "other",
  source: "manual",
  confidence: "0.8",
};

type FieldErrors = Partial<Record<keyof TechStackFormValues, string>>;

type TechStackFormProps = {
  mode?: "create" | "edit";
  initialValues?: Partial<TechStackItemCreateInput> | Partial<TechStackItem>;
  isSubmitting?: boolean;
  submitError?: unknown;
  onSubmit: (data: TechStackItemCreateInput) => Promise<void> | void;
  onCancel?: () => void;
};

function getBackendErrorMessage(error: unknown) {
  if (error instanceof ApiError) {
    return error.message;
  }
  if (error instanceof Error) {
    return error.message;
  }
  return null;
}

function toFormValues(
  values?: Partial<TechStackItemCreateInput> | Partial<TechStackItem>,
): TechStackFormValues {
  return {
    name: values?.name ?? "",
    category: (values?.category as TechStackCategory | undefined) ?? "other",
    source: (values?.source as TechStackSource | undefined) ?? "manual",
    confidence:
      values?.confidence === null || values?.confidence === undefined
        ? "0.8"
        : String(values.confidence),
  };
}

export function TechStackForm({
  mode = "create",
  initialValues,
  isSubmitting = false,
  submitError,
  onSubmit,
  onCancel,
}: TechStackFormProps) {
  const resolvedInitialValues = useMemo(
    () => toFormValues(initialValues),
    [
      initialValues?.name,
      initialValues?.category,
      initialValues?.source,
      initialValues?.confidence,
    ],
  );
  const [values, setValues] = useState<TechStackFormValues>(
    resolvedInitialValues,
  );
  const [errors, setErrors] = useState<FieldErrors>({});
  const backendError = useMemo(
    () => getBackendErrorMessage(submitError),
    [submitError],
  );

  useEffect(() => {
    setValues(resolvedInitialValues);
    setErrors({});
  }, [resolvedInitialValues]);

  function updateField<K extends keyof TechStackFormValues>(
    field: K,
    value: TechStackFormValues[K],
  ) {
    setValues((current) => ({ ...current, [field]: value }));
    setErrors((current) => ({ ...current, [field]: undefined }));
  }

  function validate() {
    const nextErrors: FieldErrors = {};
    const confidence = Number(values.confidence);

    if (!values.name.trim()) {
      nextErrors.name = "Technology name is required.";
    }
    if (!values.category) {
      nextErrors.category = "Category is required.";
    }
    if (!values.source) {
      nextErrors.source = "Source is required.";
    }
    if (
      values.confidence.trim() === "" ||
      Number.isNaN(confidence) ||
      confidence < 0 ||
      confidence > 1
    ) {
      nextErrors.confidence = "Confidence must be between 0 and 1.";
    }

    setErrors(nextErrors);
    return Object.keys(nextErrors).length === 0;
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!validate()) {
      return;
    }

    await onSubmit({
      name: values.name.trim(),
      category: values.category,
      source: values.source,
      confidence: Number(values.confidence),
    });

    if (mode === "create") {
      setValues(emptyValues);
    }
    setErrors({});
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-5">
      {backendError ? (
        <div className="rounded-md border border-[#fecaca] bg-[#fff7f7] p-3 text-sm text-[#991b1b]">
          {backendError}
        </div>
      ) : null}

      <Field label="Name" error={errors.name} required>
        <input
          value={values.name}
          onChange={(event) => updateField("name", event.target.value)}
          className="w-full rounded border border-[#c8ced8] px-3 py-2 text-sm outline-none focus:border-[#172033]"
          placeholder="Next.js"
        />
      </Field>

      <div className="grid gap-4 sm:grid-cols-2">
        <Field label="Category" error={errors.category} required>
          <select
            value={values.category}
            onChange={(event) =>
              updateField("category", event.target.value as TechStackCategory)
            }
            className="w-full rounded border border-[#c8ced8] px-3 py-2 text-sm outline-none focus:border-[#172033]"
          >
            {categoryOptions.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </Field>

        <Field label="Source" error={errors.source} required>
          <select
            value={values.source}
            onChange={(event) =>
              updateField("source", event.target.value as TechStackSource)
            }
            className="w-full rounded border border-[#c8ced8] px-3 py-2 text-sm outline-none focus:border-[#172033]"
          >
            {sourceOptions.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </Field>
      </div>

      <Field label="Confidence" error={errors.confidence} required>
        <input
          type="number"
          min={0}
          max={1}
          step={0.05}
          value={values.confidence}
          onChange={(event) => updateField("confidence", event.target.value)}
          className="w-full rounded border border-[#c8ced8] px-3 py-2 text-sm outline-none focus:border-[#172033]"
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
          {isSubmitting
            ? mode === "edit"
              ? "Saving..."
              : "Adding..."
            : mode === "edit"
              ? "Save Changes"
              : "Add Technology"}
        </button>
      </div>
    </form>
  );
}

function Field({
  label,
  error,
  required = false,
  children,
}: {
  label: string;
  error?: string;
  required?: boolean;
  children: ReactNode;
}) {
  return (
    <label className="block">
      <span className="mb-1.5 block text-sm font-medium text-[#344054]">
        {label}
        {required ? <span className="text-[#b42318]"> *</span> : null}
      </span>
      {children}
      {error ? (
        <span className="mt-1 block text-xs text-[#b42318]">{error}</span>
      ) : null}
    </label>
  );
}
