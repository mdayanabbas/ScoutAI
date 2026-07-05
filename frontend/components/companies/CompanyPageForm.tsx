"use client";

import { FormEvent, ReactNode, useEffect, useMemo, useState } from "react";

import { ApiError } from "@/lib/api";
import type {
  CompanyPageCreateInput,
  PageType,
} from "@/types/company-page";

const pageTypeOptions: Array<{ value: PageType; label: string }> = [
  { value: "homepage", label: "Homepage" },
  { value: "about", label: "About" },
  { value: "careers", label: "Careers" },
  { value: "jobs", label: "Jobs" },
  { value: "team", label: "Team" },
  { value: "blog", label: "Blog" },
  { value: "engineering", label: "Engineering" },
  { value: "docs", label: "Docs" },
  { value: "pricing", label: "Pricing" },
  { value: "unknown", label: "Unknown" },
];

type CompanyPageFormValues = {
  url: string;
  page_type: PageType;
  title: string;
  raw_text: string;
  html_hash: string;
  status_code: string;
  content_length: string;
};

const emptyValues: CompanyPageFormValues = {
  url: "",
  page_type: "unknown",
  title: "",
  raw_text: "",
  html_hash: "",
  status_code: "",
  content_length: "",
};

type FieldErrors = Partial<Record<keyof CompanyPageFormValues, string>>;

type CompanyPageFormProps = {
  mode?: "create" | "edit";
  initialValues?: Partial<CompanyPageCreateInput>;
  isSubmitting?: boolean;
  submitError?: unknown;
  onSubmit: (data: CompanyPageCreateInput) => Promise<void> | void;
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
  values?: Partial<CompanyPageCreateInput>,
): CompanyPageFormValues {
  return {
    url: values?.url ?? "",
    page_type: values?.page_type ?? "unknown",
    title: values?.title ?? "",
    raw_text: values?.raw_text ?? "",
    html_hash: values?.html_hash ?? "",
    status_code:
      values?.status_code === null || values?.status_code === undefined
        ? ""
        : String(values.status_code),
    content_length:
      values?.content_length === null || values?.content_length === undefined
        ? ""
        : String(values.content_length),
  };
}

export function CompanyPageForm({
  mode = "create",
  initialValues,
  isSubmitting = false,
  submitError,
  onSubmit,
  onCancel,
}: CompanyPageFormProps) {
  const resolvedInitialValues = useMemo(
    () => toFormValues(initialValues),
    [
      initialValues?.url,
      initialValues?.page_type,
      initialValues?.title,
      initialValues?.raw_text,
      initialValues?.html_hash,
      initialValues?.status_code,
      initialValues?.content_length,
    ],
  );
  const [values, setValues] = useState<CompanyPageFormValues>(
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

  function updateField<K extends keyof CompanyPageFormValues>(
    field: K,
    value: CompanyPageFormValues[K],
  ) {
    setValues((current) => ({ ...current, [field]: value }));
    setErrors((current) => ({ ...current, [field]: undefined }));
  }

  function validate() {
    const nextErrors: FieldErrors = {};
    const statusCode = optionalNumber(values.status_code);
    const contentLength = optionalNumber(values.content_length);

    if (!values.url.trim()) {
      nextErrors.url = "URL is required.";
    }
    if (
      statusCode !== null &&
      (!Number.isInteger(statusCode) || statusCode < 100 || statusCode > 599)
    ) {
      nextErrors.status_code = "Use a valid HTTP status code.";
    }
    if (
      contentLength !== null &&
      (!Number.isInteger(contentLength) || contentLength < 0)
    ) {
      nextErrors.content_length = "Use a whole number greater than or equal to 0.";
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
      url: values.url.trim(),
      page_type: values.page_type,
      title: optionalText(values.title),
      raw_text: optionalText(values.raw_text),
      html_hash: optionalText(values.html_hash),
      status_code: optionalNumber(values.status_code),
      content_length: optionalNumber(values.content_length),
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

      <Field label="URL" error={errors.url} required>
        <input
          value={values.url}
          onChange={(event) => updateField("url", event.target.value)}
          className="w-full rounded border border-[#c8ced8] px-3 py-2 text-sm outline-none focus:border-[#172033]"
          placeholder="https://example.com/careers"
        />
      </Field>

      <div className="grid gap-4 sm:grid-cols-2">
        <Field label="Page Type" error={errors.page_type} required>
          <select
            value={values.page_type}
            onChange={(event) =>
              updateField("page_type", event.target.value as PageType)
            }
            className="w-full rounded border border-[#c8ced8] px-3 py-2 text-sm outline-none focus:border-[#172033]"
          >
            {pageTypeOptions.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </Field>

        <Field label="Title" error={errors.title}>
          <input
            value={values.title}
            onChange={(event) => updateField("title", event.target.value)}
            className="w-full rounded border border-[#c8ced8] px-3 py-2 text-sm outline-none focus:border-[#172033]"
            placeholder="Careers"
          />
        </Field>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <Field label="Status Code" error={errors.status_code}>
          <input
            type="number"
            min={100}
            max={599}
            value={values.status_code}
            onChange={(event) => updateField("status_code", event.target.value)}
            className="w-full rounded border border-[#c8ced8] px-3 py-2 text-sm outline-none focus:border-[#172033]"
          />
        </Field>

        <Field label="Content Length" error={errors.content_length}>
          <input
            type="number"
            min={0}
            value={values.content_length}
            onChange={(event) =>
              updateField("content_length", event.target.value)
            }
            className="w-full rounded border border-[#c8ced8] px-3 py-2 text-sm outline-none focus:border-[#172033]"
          />
        </Field>
      </div>

      <Field label="HTML Hash" error={errors.html_hash}>
        <input
          value={values.html_hash}
          onChange={(event) => updateField("html_hash", event.target.value)}
          className="w-full rounded border border-[#c8ced8] px-3 py-2 text-sm outline-none focus:border-[#172033]"
        />
      </Field>

      <Field label="Raw Text" error={errors.raw_text}>
        <textarea
          value={values.raw_text}
          onChange={(event) => updateField("raw_text", event.target.value)}
          className="min-h-32 w-full rounded border border-[#c8ced8] px-3 py-2 text-sm outline-none focus:border-[#172033]"
          placeholder="Optional manually captured page text"
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
              : "Add Page"}
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
