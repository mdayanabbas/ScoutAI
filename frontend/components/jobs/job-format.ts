import type { JobListItem } from "@/types/job";

export function formatJobLabel(value: string | null | undefined) {
  if (!value) {
    return "Unknown";
  }

  return value
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

export function formatJobDate(value: string | null | undefined) {
  if (!value) {
    return "Unknown";
  }

  return new Intl.DateTimeFormat("en", {
    dateStyle: "medium",
  }).format(new Date(value));
}

export function formatExperience(job: Pick<JobListItem, "experience_min" | "experience_max">) {
  if (job.experience_min === null && job.experience_max === null) {
    return "Not specified";
  }
  if (job.experience_min !== null && job.experience_max !== null) {
    return `${job.experience_min}-${job.experience_max} years`;
  }
  if (job.experience_min !== null) {
    return `${job.experience_min}+ years`;
  }
  return `Up to ${job.experience_max} years`;
}

export function formatSalary(
  job: Pick<JobListItem, "salary_min" | "salary_max" | "salary_currency">,
) {
  if (job.salary_min === null && job.salary_max === null) {
    return "No salary listed";
  }

  const currency = job.salary_currency ?? "USD";
  const minimum =
    job.salary_min === null ? null : Number(job.salary_min).toLocaleString();
  const maximum =
    job.salary_max === null ? null : Number(job.salary_max).toLocaleString();

  if (minimum && maximum) {
    return `${currency} ${minimum}-${maximum}`;
  }
  if (minimum) {
    return `${currency} ${minimum}+`;
  }
  return `Up to ${currency} ${maximum}`;
}

export function shortCompanyId(companyId: string) {
  return companyId.length > 8 ? `${companyId.slice(0, 8)}...` : companyId;
}

export function isValidJobUrl(value: string | null | undefined) {
  if (!value) {
    return false;
  }

  try {
    const url = new URL(value);
    return url.protocol === "http:" || url.protocol === "https:";
  } catch {
    return false;
  }
}
