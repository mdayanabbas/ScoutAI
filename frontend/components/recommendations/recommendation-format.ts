import type { RecommendedJobMatch } from "@/types/job-match";

export const matchTierLabels: Record<string, string> = {
  best_match: "Best Match",
  strong_match: "Strong Match",
  worth_checking: "Worth Checking",
  stretch: "Stretch",
  unsuitable: "Unsuitable",
};

export const remoteEligibilityLabels: Record<string, string> = {
  work_from_anywhere: "Work from Anywhere",
  remote_india_eligible: "India Eligible",
  remote_global_unspecified: "Global Remote",
  remote_eligibility_unclear: "Remote Unclear",
  unknown: "Remote Unknown",
  onsite: "Onsite",
  hybrid: "Hybrid",
  remote_country_restricted: "Country Restricted",
  remote_region_restricted: "Region Restricted",
};

export const eligibilityLabels: Record<string, string> = {
  eligible: "Eligible",
  stretch: "Stretch",
  uncertain: "Uncertain",
  unsuitable: "Unsuitable",
};

export function labelize(value: string | null | undefined) {
  if (!value) {
    return "Not specified";
  }
  return value
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

export function formatMatchTier(value: string | null | undefined) {
  return value ? matchTierLabels[value] ?? labelize(value) : "Not scored";
}

export function formatRemoteEligibility(value: string | null | undefined) {
  return value ? remoteEligibilityLabels[value] ?? labelize(value) : "Remote Unknown";
}

export function formatEligibility(value: string | null | undefined) {
  return value ? eligibilityLabels[value] ?? labelize(value) : "Unknown";
}

export function formatExperience(
  job: Pick<RecommendedJobMatch, "experience_min" | "experience_max">,
) {
  if (job.experience_min == null && job.experience_max == null) {
    return "Experience not specified";
  }
  if (job.experience_min != null && job.experience_max != null) {
    return `${job.experience_min}-${job.experience_max} years`;
  }
  if (job.experience_min != null) {
    return `${job.experience_min}+ years`;
  }
  return `Up to ${job.experience_max} years`;
}

export function formatSalary(
  job: Pick<RecommendedJobMatch, "salary_min" | "salary_max" | "salary_currency">,
) {
  if (job.salary_min == null && job.salary_max == null) {
    return null;
  }
  const currency = job.salary_currency ?? "USD";
  const min = job.salary_min == null ? null : Number(job.salary_min).toLocaleString();
  const max = job.salary_max == null ? null : Number(job.salary_max).toLocaleString();
  if (min && max) {
    return `${currency} ${min}-${max}`;
  }
  if (min) {
    return `${currency} ${min}+`;
  }
  return `Up to ${currency} ${max}`;
}

export function normalizeExternalUrl(value: string | null | undefined) {
  const trimmed = value?.trim();
  if (!trimmed) {
    return null;
  }
  try {
    const url = new URL(
      /^[a-z][a-z\d+.-]*:/i.test(trimmed) ? trimmed : `https://${trimmed}`,
    );
    return url.protocol === "http:" || url.protocol === "https:"
      ? url.toString()
      : null;
  } catch {
    return null;
  }
}

export function sourceAttribution(jobUrl: string | null | undefined) {
  const url = normalizeExternalUrl(jobUrl);
  if (!url) {
    return { label: "Source: Original listing", url: null };
  }
  const host = new URL(url).hostname.replace(/^www\./, "");
  if (host === "himalayas.app") {
    return { label: "Source: Himalayas", url };
  }
  if (host === "weworkremotely.com") {
    return { label: "Source: We Work Remotely", url };
  }
  if (host === "remotive.com") {
    return { label: "Source: Remotive", url };
  }
  if (host === "ycombinator.com" || host.endsWith(".ycombinator.com")) {
    return { label: "Source: Y Combinator", url };
  }
  if (host === "jobs.ashbyhq.com") {
    return { label: "Source: Ashby", url };
  }
  return { label: "Source: Original listing", url };
}

export function applyUrlForJob(job: RecommendedJobMatch) {
  if (job.valid_apply_url !== false) {
    const applyUrl = normalizeExternalUrl(job.apply_url);
    if (applyUrl) {
      return applyUrl;
    }
  }
  if (job.valid_job_url !== false) {
    return normalizeExternalUrl(job.job_url);
  }
  return null;
}
