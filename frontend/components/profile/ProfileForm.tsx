"use client";

import { FormEvent, ReactNode, useEffect, useMemo, useState } from "react";

import { TagInput } from "@/components/profile/TagInput";
import { ApiError } from "@/lib/api";
import type {
  RemotePreference,
  UserProfile,
  UserProfileCreateInput,
} from "@/types/profile";

const targetRoleSuggestions = [
  "AI Engineer",
  "Backend Engineer",
  "Software Engineer",
  "Machine Learning Engineer",
  "Data Engineer",
  "Full Stack Engineer",
  "Product Engineer",
  "DevOps Engineer",
  "Forward Deployed Engineer",
];

const locationSuggestions = [
  "Remote",
  "Worldwide",
  "United States",
  "United Kingdom",
  "European Union",
  "India",
  "Canada",
  "Germany",
  "Netherlands",
  "Berlin",
  "London",
  "New York",
  "San Francisco",
];

const skillSuggestions = [
  "Python",
  "FastAPI",
  "PostgreSQL",
  "SQLAlchemy",
  "Docker",
  "Next.js",
  "LLMs",
  "AI Agents",
];

const remoteOptions: Array<{ value: RemotePreference; label: string }> = [
  { value: "unknown", label: "Unknown" },
  { value: "onsite", label: "On-site" },
  { value: "hybrid", label: "Hybrid" },
  { value: "remote_country", label: "Remote within country" },
  { value: "remote_region", label: "Remote within region" },
  { value: "remote_worldwide", label: "Remote worldwide" },
];

const stageOptions = [
  { value: "unknown", label: "Unknown" },
  { value: "pre_seed", label: "Pre-seed" },
  { value: "seed", label: "Seed" },
  { value: "series_a", label: "Series A" },
  { value: "series_b", label: "Series B" },
  { value: "growth", label: "Growth" },
  { value: "public", label: "Public" },
];

const sizeOptions = ["1-10", "11-50", "51-200", "201-500", "501-1000", "1000+"];

type ProfileFormValues = UserProfileCreateInput;
type FieldErrors = Partial<Record<keyof ProfileFormValues | "skill_relationships", string>>;

const emptyValues: ProfileFormValues = {
  display_name: "",
  target_roles: [],
  preferred_locations: [],
  remote_preference: "unknown",
  years_experience: 0,
  skills: [],
  strong_skills: [],
  weak_skills: [],
  preferred_company_stages: [],
  preferred_company_sizes: [],
};

type ProfileFormProps = {
  mode: "create" | "edit";
  initialValues?: UserProfile | null;
  onSubmit: (data: UserProfileCreateInput) => Promise<void> | void;
  isSubmitting?: boolean;
  apiError?: unknown;
  successMessage?: string | null;
};

function list(value: string[] | null | undefined) {
  return value ?? [];
}

function toFormValues(profile?: UserProfile | null): ProfileFormValues {
  if (!profile) {
    return emptyValues;
  }

  return {
    display_name: profile.display_name ?? "",
    target_roles: list(profile.target_roles),
    preferred_locations: list(profile.preferred_locations),
    remote_preference: profile.remote_preference ?? "unknown",
    years_experience: profile.years_experience ?? 0,
    skills: list(profile.skills),
    strong_skills: list(profile.strong_skills),
    weak_skills: list(profile.weak_skills),
    preferred_company_stages: list(profile.preferred_company_stages),
    preferred_company_sizes: list(profile.preferred_company_sizes),
  };
}

function normalizedValues(values: ProfileFormValues) {
  return {
    ...values,
    display_name: values.display_name.trim(),
    target_roles: values.target_roles.map((item) => item.trim()).filter(Boolean),
    preferred_locations: values.preferred_locations
      .map((item) => item.trim())
      .filter(Boolean),
    skills: values.skills.map((item) => item.trim()).filter(Boolean),
    strong_skills: values.strong_skills.map((item) => item.trim()).filter(Boolean),
    weak_skills: values.weak_skills.map((item) => item.trim()).filter(Boolean),
    years_experience: Number(values.years_experience),
  };
}

function backendError(error: unknown) {
  if (error instanceof ApiError || error instanceof Error) {
    return error.message;
  }
  return null;
}

function lowerSet(values: string[]) {
  return new Set(values.map((value) => value.toLowerCase()));
}

export function ProfileForm({
  mode,
  initialValues,
  onSubmit,
  isSubmitting = false,
  apiError,
  successMessage,
}: ProfileFormProps) {
  const initialFormValues = useMemo(
    () => toFormValues(initialValues),
    [initialValues],
  );
  const [values, setValues] = useState<ProfileFormValues>(initialFormValues);
  const [errors, setErrors] = useState<FieldErrors>({});
  const savedSnapshot = useMemo(
    () => JSON.stringify(normalizedValues(initialFormValues)),
    [initialFormValues],
  );
  const currentSnapshot = JSON.stringify(normalizedValues(values));
  const hasChanges = mode === "create" || currentSnapshot !== savedSnapshot;
  const apiErrorMessage = backendError(apiError);

  useEffect(() => {
    setValues(initialFormValues);
    setErrors({});
  }, [initialFormValues]);

  function update<K extends keyof ProfileFormValues>(
    field: K,
    value: ProfileFormValues[K],
  ) {
    setValues((current) => ({ ...current, [field]: value }));
    setErrors((current) => ({ ...current, [field]: undefined }));
  }

  function validate() {
    const nextErrors: FieldErrors = {};
    const cleaned = normalizedValues(values);
    const skills = lowerSet(cleaned.skills);
    const weakSkills = lowerSet(cleaned.weak_skills);

    if (!cleaned.display_name) {
      nextErrors.display_name = "Display name is required.";
    }
    if (!Number.isInteger(cleaned.years_experience) || cleaned.years_experience < 0) {
      nextErrors.years_experience =
        "Years of experience must be a whole number greater than or equal to 0.";
    }
    if (cleaned.target_roles.length === 0) {
      nextErrors.target_roles = "Add at least one target role.";
    }
    if (!remoteOptions.some((option) => option.value === cleaned.remote_preference)) {
      nextErrors.remote_preference = "Choose a supported remote preference.";
    }

    const overlap = cleaned.strong_skills.filter((skill) =>
      weakSkills.has(skill.toLowerCase()),
    );
    const missingStrong = cleaned.strong_skills.filter(
      (skill) => !skills.has(skill.toLowerCase()),
    );
    const missingWeak = cleaned.weak_skills.filter(
      (skill) => !skills.has(skill.toLowerCase()),
    );

    if (overlap.length > 0) {
      nextErrors.skill_relationships =
        "The same skill cannot be both strong and weak.";
    } else if (missingStrong.length > 0 || missingWeak.length > 0) {
      nextErrors.skill_relationships =
        "Strong and weak skills should also be listed in Skills.";
    }

    setErrors(nextErrors);
    return Object.keys(nextErrors).length === 0;
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!validate()) {
      return;
    }
    await onSubmit(normalizedValues(values));
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-5">
      {hasChanges && mode === "edit" ? (
        <div className="rounded-md border border-[#fedf89] bg-[#fffbeb] p-3 text-sm text-[#92400e]">
          Unsaved changes
        </div>
      ) : null}
      {successMessage ? (
        <div className="rounded-md border border-[#bbf7d0] bg-[#f0fdf4] p-3 text-sm text-[#166534]">
          {successMessage}
        </div>
      ) : null}
      {apiErrorMessage ? (
        <div className="rounded-md border border-[#fecaca] bg-[#fff7f7] p-3 text-sm text-[#991b1b]">
          {apiErrorMessage}
        </div>
      ) : null}

      <FormSection title="Basic Information">
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="Display Name" error={errors.display_name} required>
            <input
              value={values.display_name}
              onChange={(event) => update("display_name", event.target.value)}
              className="w-full rounded border border-[#c8ced8] px-3 py-2 text-sm outline-none focus:border-[#172033]"
            />
          </Field>
          <Field label="Years Experience" error={errors.years_experience}>
            <input
              type="number"
              min={0}
              step={1}
              value={values.years_experience}
              onChange={(event) =>
                update("years_experience", Number(event.target.value))
              }
              className="w-full rounded border border-[#c8ced8] px-3 py-2 text-sm outline-none focus:border-[#172033]"
            />
          </Field>
        </div>
      </FormSection>

      <FormSection title="Role Preferences">
        <TagInput
          label="Target Roles"
          values={values.target_roles}
          onChange={(next) => update("target_roles", next)}
          suggestions={targetRoleSuggestions}
          placeholder="Backend Engineer"
          error={errors.target_roles}
        />
        <TagInput
          label="Preferred Locations"
          values={values.preferred_locations}
          onChange={(next) => update("preferred_locations", next)}
          suggestions={locationSuggestions}
          placeholder="Remote"
        />
        <Field label="Remote Preference" error={errors.remote_preference}>
          <select
            value={values.remote_preference}
            onChange={(event) =>
              update("remote_preference", event.target.value as RemotePreference)
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
      </FormSection>

      <FormSection title="Skills">
        <TagInput
          label="Skills"
          values={values.skills}
          onChange={(next) => update("skills", next)}
          suggestions={skillSuggestions}
          placeholder="Python"
        />
        <TagInput
          label="Strong Skills"
          values={values.strong_skills}
          onChange={(next) => update("strong_skills", next)}
          suggestions={values.skills}
          placeholder="FastAPI"
        />
        <TagInput
          label="Weak Skills"
          values={values.weak_skills}
          onChange={(next) => update("weak_skills", next)}
          suggestions={values.skills}
          placeholder="Kubernetes"
          error={errors.skill_relationships}
        />
      </FormSection>

      <FormSection title="Startup Preferences">
        <CheckboxGroup
          label="Preferred Company Stages"
          values={values.preferred_company_stages}
          options={stageOptions}
          onChange={(next) => update("preferred_company_stages", next)}
        />
        <CheckboxGroup
          label="Preferred Company Sizes"
          values={values.preferred_company_sizes}
          options={sizeOptions.map((value) => ({ value, label: value }))}
          onChange={(next) => update("preferred_company_sizes", next)}
        />
      </FormSection>

      <div className="flex justify-end border-t border-[#edf0f5] pt-5">
        <button
          type="submit"
          disabled={isSubmitting || !hasChanges}
          className="rounded bg-[#172033] px-4 py-2 text-sm font-medium text-white hover:bg-[#24314a] disabled:cursor-not-allowed disabled:opacity-60"
        >
          {isSubmitting
            ? "Saving..."
            : mode === "create"
              ? "Create Profile"
              : "Save Changes"}
        </button>
      </div>
    </form>
  );
}

function FormSection({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="space-y-4 rounded-md border border-[#d9dee8] bg-white p-4">
      <h2 className="text-base font-semibold text-[#171923]">{title}</h2>
      {children}
    </section>
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

function CheckboxGroup({
  label,
  values,
  options,
  onChange,
}: {
  label: string;
  values: string[];
  options: Array<{ value: string; label: string }>;
  onChange: (values: string[]) => void;
}) {
  function toggle(value: string) {
    onChange(
      values.includes(value)
        ? values.filter((item) => item !== value)
        : [...values, value],
    );
  }

  return (
    <div>
      <h3 className="mb-2 text-sm font-medium text-[#344054]">{label}</h3>
      <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
        {options.map((option) => (
          <label
            key={option.value}
            className="flex items-center gap-2 rounded border border-[#d9dee8] px-3 py-2 text-sm text-[#475467]"
          >
            <input
              type="checkbox"
              checked={values.includes(option.value)}
              onChange={() => toggle(option.value)}
            />
            {option.label}
          </label>
        ))}
      </div>
    </div>
  );
}
