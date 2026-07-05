"use client";

import { FormEvent, ReactNode, useEffect, useMemo, useState } from "react";

import { ApiError } from "@/lib/api";
import type {
  Job,
  JobCreateInput,
  JobStatus,
  RemoteType,
  RoleCategory,
} from "@/types/job";

const roleOptions: Array<{ value: RoleCategory; label: string }> = [
  { value: "ai_engineer", label: "AI Engineer" },
  { value: "backend_engineer", label: "Backend Engineer" },
  { value: "software_engineer", label: "Software Engineer" },
  { value: "ml_engineer", label: "ML Engineer" },
  { value: "data_engineer", label: "Data Engineer" },
  { value: "full_stack_engineer", label: "Full Stack Engineer" },
  { value: "frontend_engineer", label: "Frontend Engineer" },
  { value: "devops_engineer", label: "DevOps Engineer" },
  { value: "product_engineer", label: "Product Engineer" },
  { value: "other", label: "Other" },
];

const remoteOptions: Array<{ value: RemoteType; label: string }> = [
  { value: "unknown", label: "Unknown" },
  { value: "onsite", label: "Onsite" },
  { value: "hybrid", label: "Hybrid" },
  { value: "remote_country", label: "Remote Country" },
  { value: "remote_region", label: "Remote Region" },
  { value: "remote_worldwide", label: "Remote Worldwide" },
];

const statusOptions: Array<{ value: JobStatus; label: string }> = [
  { value: "active", label: "Active" },
  { value: "inactive", label: "Inactive" },
  { value: "expired", label: "Expired" },
  { value: "unknown", label: "Unknown" },
];

type JobFormValues = {
  title: string;
  role_category: RoleCategory;
  description: string;
  location: string;
  remote_type: RemoteType;
  experience_min: string;
  experience_max: string;
  salary_min: string;
  salary_max: string;
  salary_currency: string;
  job_url: string;
  source_platform: string;
  status: JobStatus;
};

const emptyValues: JobFormValues = {
  title: "",
  role_category: "other",
  description: "",
  location: "",
  remote_type: "unknown",
  experience_min: "",
  experience_max: "",
  salary_min: "",
  salary_max: "",
  salary_currency: "USD",
  job_url: "",
  source_platform: "company_website",
  status: "active",
};

type FieldErrors = Partial<Record<keyof JobFormValues, string>>;

type JobFormProps = {
  mode?: "create" | "edit";
  initialValues?: Partial<JobCreateInput> | Partial<Job>;
  isSubmitting?: boolean;
  submitError?: unknown;
  onSubmit: (data: JobCreateInput) => Promise<void> | void;
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

function toFormValues(values?: Partial<JobCreateInput> | Partial<Job>): JobFormValues {
  return {
    title: values?.title ?? "",
    role_category: values?.role_category ?? "other",
    description: values?.description ?? "",
    location: values?.location ?? "",
    remote_type: values?.remote_type ?? "unknown",
    experience_min:
      values?.experience_min === null || values?.experience_min === undefined
        ? ""
        : String(values.experience_min),
    experience_max:
      values?.experience_max === null || values?.experience_max === undefined
        ? ""
        : String(values.experience_max),
    salary_min:
      values?.salary_min === null || values?.salary_min === undefined
        ? ""
        : String(values.salary_min),
    salary_max:
      values?.salary_max === null || values?.salary_max === undefined
        ? ""
        : String(values.salary_max),
    salary_currency: values?.salary_currency ?? "USD",
    job_url: values?.job_url ?? "",
    source_platform: values?.source_platform ?? "company_website",
    status: values?.status ?? "active",
  };
}

export function JobForm({
  mode = "create",
  initialValues,
  isSubmitting = false,
  submitError,
  onSubmit,
  onCancel,
}: JobFormProps) {
  const resolvedInitialValues = useMemo(
    () => toFormValues(initialValues),
    [
      initialValues?.title,
      initialValues?.role_category,
      initialValues?.description,
      initialValues?.location,
      initialValues?.remote_type,
      initialValues?.experience_min,
      initialValues?.experience_max,
      initialValues?.salary_min,
      initialValues?.salary_max,
      initialValues?.salary_currency,
      initialValues?.job_url,
      initialValues?.source_platform,
      initialValues?.status,
    ],
  );
  const [values, setValues] = useState<JobFormValues>(resolvedInitialValues);
  const [errors, setErrors] = useState<FieldErrors>({});
  const backendError = useMemo(
    () => getBackendErrorMessage(submitError),
    [submitError],
  );

  useEffect(() => {
    setValues(resolvedInitialValues);
    setErrors({});
  }, [resolvedInitialValues]);

  function updateField<K extends keyof JobFormValues>(
    field: K,
    value: JobFormValues[K],
  ) {
    setValues((current) => ({ ...current, [field]: value }));
    setErrors((current) => ({ ...current, [field]: undefined }));
  }

  function validate() {
    const nextErrors: FieldErrors = {};
    const experienceMin = optionalNumber(values.experience_min);
    const experienceMax = optionalNumber(values.experience_max);
    const salaryMin = optionalNumber(values.salary_min);
    const salaryMax = optionalNumber(values.salary_max);

    if (!values.title.trim()) {
      nextErrors.title = "Title is required.";
    }
    if (!values.job_url.trim()) {
      nextErrors.job_url = "Job URL is required.";
    }
    if (
      experienceMin !== null &&
      (!Number.isInteger(experienceMin) || experienceMin < 0)
    ) {
      nextErrors.experience_min = "Use a whole number greater than or equal to 0.";
    }
    if (
      experienceMax !== null &&
      (!Number.isInteger(experienceMax) || experienceMax < 0)
    ) {
      nextErrors.experience_max = "Use a whole number greater than or equal to 0.";
    }
    if (
      experienceMin !== null &&
      experienceMax !== null &&
      experienceMin > experienceMax
    ) {
      nextErrors.experience_max = "Max experience must be greater than min.";
    }
    if (salaryMin !== null && salaryMin < 0) {
      nextErrors.salary_min = "Salary must be greater than or equal to 0.";
    }
    if (salaryMax !== null && salaryMax < 0) {
      nextErrors.salary_max = "Salary must be greater than or equal to 0.";
    }
    if (salaryMin !== null && salaryMax !== null && salaryMin > salaryMax) {
      nextErrors.salary_max = "Max salary must be greater than min.";
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
      title: values.title.trim(),
      role_category: values.role_category,
      description: optionalText(values.description),
      location: optionalText(values.location),
      remote_type: values.remote_type,
      experience_min: optionalNumber(values.experience_min),
      experience_max: optionalNumber(values.experience_max),
      salary_min: optionalNumber(values.salary_min),
      salary_max: optionalNumber(values.salary_max),
      salary_currency: optionalText(values.salary_currency),
      job_url: values.job_url.trim(),
      source_platform: optionalText(values.source_platform),
      status: values.status,
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

      <div className="grid gap-4 sm:grid-cols-2">
        <Field label="Title" error={errors.title} required>
          <input
            value={values.title}
            onChange={(event) => updateField("title", event.target.value)}
            className="w-full rounded border border-[#c8ced8] px-3 py-2 text-sm outline-none focus:border-[#172033]"
            placeholder="AI Engineer"
          />
        </Field>

        <Field label="Job URL" error={errors.job_url} required>
          <input
            value={values.job_url}
            onChange={(event) => updateField("job_url", event.target.value)}
            className="w-full rounded border border-[#c8ced8] px-3 py-2 text-sm outline-none focus:border-[#172033]"
            placeholder="https://example.com/jobs/ai-engineer"
          />
        </Field>
      </div>

      <Field label="Description" error={errors.description}>
        <textarea
          value={values.description}
          onChange={(event) => updateField("description", event.target.value)}
          className="min-h-32 w-full rounded border border-[#c8ced8] px-3 py-2 text-sm outline-none focus:border-[#172033]"
        />
      </Field>

      <div className="grid gap-4 sm:grid-cols-3">
        <Field label="Role Category" error={errors.role_category}>
          <select
            value={values.role_category}
            onChange={(event) =>
              updateField("role_category", event.target.value as RoleCategory)
            }
            className="w-full rounded border border-[#c8ced8] px-3 py-2 text-sm outline-none focus:border-[#172033]"
          >
            {roleOptions.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </Field>

        <Field label="Remote Type" error={errors.remote_type}>
          <select
            value={values.remote_type}
            onChange={(event) =>
              updateField("remote_type", event.target.value as RemoteType)
            }
            className="w-full rounded border border-[#c8ced8] px-3 py-2 text-sm outline-none focus:border-[#172033]"
          >
            {remoteOptions.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </Field>

        <Field label="Status" error={errors.status}>
          <select
            value={values.status}
            onChange={(event) =>
              updateField("status", event.target.value as JobStatus)
            }
            className="w-full rounded border border-[#c8ced8] px-3 py-2 text-sm outline-none focus:border-[#172033]"
          >
            {statusOptions.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </Field>
      </div>

      <div className="grid gap-4 sm:grid-cols-3">
        <Field label="Location" error={errors.location}>
          <input
            value={values.location}
            onChange={(event) => updateField("location", event.target.value)}
            className="w-full rounded border border-[#c8ced8] px-3 py-2 text-sm outline-none focus:border-[#172033]"
          />
        </Field>
        <Field label="Min Experience" error={errors.experience_min}>
          <input
            type="number"
            min={0}
            value={values.experience_min}
            onChange={(event) =>
              updateField("experience_min", event.target.value)
            }
            className="w-full rounded border border-[#c8ced8] px-3 py-2 text-sm outline-none focus:border-[#172033]"
          />
        </Field>
        <Field label="Max Experience" error={errors.experience_max}>
          <input
            type="number"
            min={0}
            value={values.experience_max}
            onChange={(event) =>
              updateField("experience_max", event.target.value)
            }
            className="w-full rounded border border-[#c8ced8] px-3 py-2 text-sm outline-none focus:border-[#172033]"
          />
        </Field>
      </div>

      <div className="grid gap-4 sm:grid-cols-4">
        <Field label="Min Salary" error={errors.salary_min}>
          <input
            type="number"
            min={0}
            value={values.salary_min}
            onChange={(event) => updateField("salary_min", event.target.value)}
            className="w-full rounded border border-[#c8ced8] px-3 py-2 text-sm outline-none focus:border-[#172033]"
          />
        </Field>
        <Field label="Max Salary" error={errors.salary_max}>
          <input
            type="number"
            min={0}
            value={values.salary_max}
            onChange={(event) => updateField("salary_max", event.target.value)}
            className="w-full rounded border border-[#c8ced8] px-3 py-2 text-sm outline-none focus:border-[#172033]"
          />
        </Field>
        <Field label="Currency" error={errors.salary_currency}>
          <input
            value={values.salary_currency}
            onChange={(event) =>
              updateField("salary_currency", event.target.value)
            }
            className="w-full rounded border border-[#c8ced8] px-3 py-2 text-sm outline-none focus:border-[#172033]"
          />
        </Field>
        <Field label="Source" error={errors.source_platform}>
          <input
            value={values.source_platform}
            onChange={(event) =>
              updateField("source_platform", event.target.value)
            }
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
          {isSubmitting
            ? mode === "edit"
              ? "Saving..."
              : "Adding..."
            : mode === "edit"
              ? "Save Changes"
              : "Add Job"}
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
