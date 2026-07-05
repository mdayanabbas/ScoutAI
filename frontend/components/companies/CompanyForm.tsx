"use client";

import { FormEvent, ReactNode, useMemo, useState } from "react";

import { ApiError } from "@/lib/api";
import type {
  CompanyCreateInput,
  CompanySource,
  CompanyStage,
} from "@/types/company";

const stageOptions: Array<{ value: CompanyStage; label: string }> = [
  { value: "unknown", label: "Unknown" },
  { value: "pre_seed", label: "Pre-seed" },
  { value: "seed", label: "Seed" },
  { value: "series_a", label: "Series A" },
  { value: "series_b", label: "Series B" },
  { value: "growth", label: "Growth" },
  { value: "public", label: "Public" },
];

const sourceOptions: Array<{ value: CompanySource; label: string }> = [
  { value: "manual", label: "Manual" },
  { value: "yc", label: "YC" },
  { value: "product_hunt", label: "Product Hunt" },
  { value: "hacker_news", label: "Hacker News" },
  { value: "wellfound", label: "Wellfound" },
  { value: "company_website", label: "Company Website" },
  { value: "rss", label: "RSS" },
  { value: "other", label: "Other" },
];

type CompanyFormValues = {
  name: string;
  website_url: string;
  description: string;
  country: string;
  city: string;
  stage: CompanyStage;
  source: CompanySource;
  employee_count_min: string;
  employee_count_max: string;
  founded_year: string;
  is_active: boolean;
};

const initialValues: CompanyFormValues = {
  name: "",
  website_url: "",
  description: "",
  country: "",
  city: "",
  stage: "unknown",
  source: "manual",
  employee_count_min: "",
  employee_count_max: "",
  founded_year: "",
  is_active: true,
};

type FieldErrors = Partial<Record<keyof CompanyFormValues, string>>;

type CompanyFormProps = {
  isSubmitting?: boolean;
  submitError?: unknown;
  onSubmit: (data: CompanyCreateInput) => Promise<void> | void;
  onCancel?: () => void;
};

function optionalNumber(value: string) {
  if (value.trim() === "") {
    return null;
  }
  return Number(value);
}

function optionalText(value: string) {
  const trimmed = value.trim();
  return trimmed === "" ? null : trimmed;
}

function getBackendErrorMessage(error: unknown) {
  if (error instanceof ApiError) {
    if (error.status === 409) {
      return error.message || "A company with this domain already exists.";
    }
    return error.message;
  }

  if (error instanceof Error) {
    return error.message;
  }

  return null;
}

export function CompanyForm({
  isSubmitting = false,
  submitError,
  onSubmit,
  onCancel,
}: CompanyFormProps) {
  const [values, setValues] = useState<CompanyFormValues>(initialValues);
  const [errors, setErrors] = useState<FieldErrors>({});

  const backendError = useMemo(
    () => getBackendErrorMessage(submitError),
    [submitError],
  );

  function updateField<K extends keyof CompanyFormValues>(
    field: K,
    value: CompanyFormValues[K],
  ) {
    setValues((current) => ({ ...current, [field]: value }));
    setErrors((current) => ({ ...current, [field]: undefined }));
  }

  function validate() {
    const nextErrors: FieldErrors = {};
    const minEmployees = optionalNumber(values.employee_count_min);
    const maxEmployees = optionalNumber(values.employee_count_max);
    const foundedYear = optionalNumber(values.founded_year);
    const currentYear = new Date().getFullYear();

    if (!values.name.trim()) {
      nextErrors.name = "Company name is required.";
    }
    if (!values.website_url.trim()) {
      nextErrors.website_url = "Website URL is required.";
    }
    if (minEmployees !== null && (!Number.isInteger(minEmployees) || minEmployees < 0)) {
      nextErrors.employee_count_min = "Use a whole number greater than or equal to 0.";
    }
    if (maxEmployees !== null && (!Number.isInteger(maxEmployees) || maxEmployees < 0)) {
      nextErrors.employee_count_max = "Use a whole number greater than or equal to 0.";
    }
    if (
      minEmployees !== null &&
      maxEmployees !== null &&
      minEmployees > maxEmployees
    ) {
      nextErrors.employee_count_max = "Max employees must be greater than min.";
    }
    if (
      foundedYear !== null &&
      (!Number.isInteger(foundedYear) ||
        foundedYear < 1800 ||
        foundedYear > currentYear)
    ) {
      nextErrors.founded_year = `Use a year between 1800 and ${currentYear}.`;
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
      website_url: values.website_url.trim(),
      description: optionalText(values.description),
      country: optionalText(values.country),
      city: optionalText(values.city),
      stage: values.stage,
      source: values.source,
      employee_count_min: optionalNumber(values.employee_count_min),
      employee_count_max: optionalNumber(values.employee_count_max),
      founded_year: optionalNumber(values.founded_year),
      is_active: values.is_active,
    });
    setValues(initialValues);
    setErrors({});
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-5">
      {backendError ? (
        <div className="rounded-md border border-[#fecaca] bg-[#fff7f7] p-3 text-sm text-[#991b1b]">
          {backendError}
        </div>
      ) : null}

      <div className="grid gap-4 sm:grid-cols-2">
        <Field label="Name" error={errors.name} required>
          <input
            value={values.name}
            onChange={(event) => updateField("name", event.target.value)}
            className="w-full rounded border border-[#c8ced8] px-3 py-2 text-sm outline-none focus:border-[#172033]"
            placeholder="Acme AI"
          />
        </Field>

        <Field label="Website URL" error={errors.website_url} required>
          <input
            value={values.website_url}
            onChange={(event) => updateField("website_url", event.target.value)}
            className="w-full rounded border border-[#c8ced8] px-3 py-2 text-sm outline-none focus:border-[#172033]"
            placeholder="https://acme.ai"
          />
        </Field>
      </div>

      <Field label="Description" error={errors.description}>
        <textarea
          value={values.description}
          onChange={(event) => updateField("description", event.target.value)}
          className="min-h-24 w-full rounded border border-[#c8ced8] px-3 py-2 text-sm outline-none focus:border-[#172033]"
          placeholder="What does this company do?"
        />
      </Field>

      <div className="grid gap-4 sm:grid-cols-2">
        <Field label="Country" error={errors.country}>
          <input
            value={values.country}
            onChange={(event) => updateField("country", event.target.value)}
            className="w-full rounded border border-[#c8ced8] px-3 py-2 text-sm outline-none focus:border-[#172033]"
            placeholder="United States"
          />
        </Field>

        <Field label="City" error={errors.city}>
          <input
            value={values.city}
            onChange={(event) => updateField("city", event.target.value)}
            className="w-full rounded border border-[#c8ced8] px-3 py-2 text-sm outline-none focus:border-[#172033]"
            placeholder="San Francisco"
          />
        </Field>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <Field label="Stage" error={errors.stage}>
          <select
            value={values.stage}
            onChange={(event) =>
              updateField("stage", event.target.value as CompanyStage)
            }
            className="w-full rounded border border-[#c8ced8] px-3 py-2 text-sm outline-none focus:border-[#172033]"
          >
            {stageOptions.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </Field>

        <Field label="Source" error={errors.source}>
          <select
            value={values.source}
            onChange={(event) =>
              updateField("source", event.target.value as CompanySource)
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

      <div className="grid gap-4 sm:grid-cols-3">
        <Field label="Min Employees" error={errors.employee_count_min}>
          <input
            type="number"
            min={0}
            value={values.employee_count_min}
            onChange={(event) =>
              updateField("employee_count_min", event.target.value)
            }
            className="w-full rounded border border-[#c8ced8] px-3 py-2 text-sm outline-none focus:border-[#172033]"
          />
        </Field>

        <Field label="Max Employees" error={errors.employee_count_max}>
          <input
            type="number"
            min={0}
            value={values.employee_count_max}
            onChange={(event) =>
              updateField("employee_count_max", event.target.value)
            }
            className="w-full rounded border border-[#c8ced8] px-3 py-2 text-sm outline-none focus:border-[#172033]"
          />
        </Field>

        <Field label="Founded Year" error={errors.founded_year}>
          <input
            type="number"
            min={1800}
            value={values.founded_year}
            onChange={(event) => updateField("founded_year", event.target.value)}
            className="w-full rounded border border-[#c8ced8] px-3 py-2 text-sm outline-none focus:border-[#172033]"
          />
        </Field>
      </div>

      <label className="flex items-center gap-3 text-sm font-medium text-[#344054]">
        <input
          type="checkbox"
          checked={values.is_active}
          onChange={(event) => updateField("is_active", event.target.checked)}
          className="h-4 w-4 rounded border-[#c8ced8]"
        />
        Active
      </label>

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
          {isSubmitting ? "Creating..." : "Create Company"}
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
      {error ? <span className="mt-1 block text-xs text-[#b42318]">{error}</span> : null}
    </label>
  );
}
