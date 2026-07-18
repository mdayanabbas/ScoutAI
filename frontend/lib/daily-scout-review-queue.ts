import type { CompanyWatchlistResponse } from "@/types/company-watchlist";
import type { RemoteJobDiscoveryOrchestratorResult, RemoteDiscoveryTopRecommendation } from "@/types/discovery";
import type { JobApplicationDecisionResponse, JobDecisionListItem, JobDecisionStatus } from "@/types/job-decision";
import type { RecommendedJobMatch } from "@/types/job-match";

export type DailyScoutReviewStatus =
  | "unreviewed"
  | "saved"
  | "interested"
  | "applied"
  | "skipped"
  | "not_interested"
  | "needs_custom_resume"
  | "needs_cold_dm"
  | "watched_company"
  | "opened_workspace";

export type DailyScoutReviewItem = {
  job_id: string;
  title: string;
  company_name: string | null;
  company_id?: string | null;
  source_platform?: string | null;
  remote_eligibility?: string | null;
  match_tier?: string | null;
  eligibility_status?: string | null;
  total_score?: number | null;
  eligibility_reason?: string | null;
  salary_min?: number | string | null;
  salary_max?: number | string | null;
  salary_currency?: string | null;
  job_url?: string | null;
  apply_url?: string | null;
  decision?: JobApplicationDecisionResponse | JobDecisionListItem | null;
  decision_id?: string | null;
  decision_status?: JobDecisionStatus | null;
  company_watch_status?: string | null;
  review_status: DailyScoutReviewStatus;
  source_run_id?: string | null;
  source_name?: string | null;
  created_from: "top_recommendations" | "source_job_ids" | "fallback_recommendations";
  raw: unknown;
  resume_fit_score?: number | null;
  resume_fit_tier?: ResumeFitTier;
  resume_fit_summary?: string | null;
  resume_strengths?: string[];
  resume_gaps?: string[];
  resume_bullet_sources?: string[];
  resume_action?: ResumeAction;
  resume_analysis_status?: ResumeAnalysisStatus;
  resume_analysis_error?: string | null;
};

export type ResumeFitTier =
  | "strong_fit"
  | "good_fit"
  | "needs_tailoring"
  | "weak_fit"
  | "unknown";

export type ResumeAction =
  | "apply_now"
  | "tailor_resume"
  | "create_project_angle"
  | "cold_dm_first"
  | "skip_for_now"
  | "needs_review";

export type ResumeAnalysisStatus =
  | "not_started"
  | "loading"
  | "ready"
  | "failed"
  | "unavailable";

export type DailyScoutReviewState = {
  job_id: string;
  review_status: DailyScoutReviewStatus;
  last_action_at: string;
};

export const dailyScoutReviewStorageKey = "scoutai.dailyScout.reviewQueue.v1";

export function buildDailyScoutReviewQueue(
  result: RemoteJobDiscoveryOrchestratorResult | null | undefined,
  existingDecisions: Array<JobApplicationDecisionResponse | JobDecisionListItem> = [],
  existingWatchlist: CompanyWatchlistResponse[] = [],
  fallbackRecommendations: RecommendedJobMatch[] = [],
  reviewState: DailyScoutReviewState[] = getDailyScoutReviewState(),
  includeSkipped = false,
) {
  const byJobId = new Map<string, DailyScoutReviewItem>();
  const decisionsByJobId = new Map(existingDecisions.map((decision) => [decision.job_id, decision]));
  const watchByCompanyId = new Map(
    existingWatchlist
      .filter((item) => item.company_id)
      .map((item) => [String(item.company_id), item]),
  );
  const stateByJobId = new Map(reviewState.map((state) => [state.job_id, state]));

  for (const recommendation of result?.top_recommendations ?? []) {
    addItem(byJobId, fromTopRecommendation(recommendation));
  }

  if (!byJobId.size) {
    for (const recommendation of fallbackRecommendations) {
      addItem(byJobId, fromFallbackRecommendation(recommendation));
    }
  }

  return Array.from(byJobId.values())
    .map((item) => {
      const decision = decisionsByJobId.get(item.job_id) ?? null;
      const watch = item.company_id ? watchByCompanyId.get(item.company_id) : null;
      const persisted = stateByJobId.get(item.job_id);
      const decisionStatus = decisionStatusValue(decision);
      return {
        ...item,
        decision,
        decision_id: decision?.id ?? null,
        decision_status: decisionStatus,
        company_watch_status: watch?.watch_status ?? item.company_watch_status ?? null,
        review_status:
          persisted?.review_status ??
          decisionReviewStatus(decisionStatus) ??
          (watch ? "watched_company" : "unreviewed"),
      };
    })
    .filter((item) => includeSkipped || !isHiddenByDefault(item))
    .sort(recommendedSort);
}

export function getDailyScoutReviewState(): DailyScoutReviewState[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = window.localStorage.getItem(dailyScoutReviewStorageKey);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed.filter(isReviewState) : [];
  } catch {
    return [];
  }
}

export function saveDailyScoutReviewState(states: DailyScoutReviewState[]) {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(dailyScoutReviewStorageKey, JSON.stringify(states));
  } catch {
    // Review state is a convenience cache; failing to persist should not block the UI.
  }
}

export function upsertDailyScoutReviewState(
  states: DailyScoutReviewState[],
  jobId: string,
  reviewStatus: DailyScoutReviewStatus,
) {
  const next = states.filter((state) => state.job_id !== jobId);
  next.push({
    job_id: jobId,
    review_status: reviewStatus,
    last_action_at: new Date().toISOString(),
  });
  saveDailyScoutReviewState(next);
  return next;
}

export function reviewStatusFromDecisionStatus(status: JobDecisionStatus): DailyScoutReviewStatus {
  if (status === "needs_custom_resume") return "needs_custom_resume";
  if (status === "needs_cold_dm") return "needs_cold_dm";
  if (status === "not_interested") return "not_interested";
  if (status === "applied") return "applied";
  if (status === "skipped") return "skipped";
  if (status === "interested") return "interested";
  return "saved";
}

function addItem(map: Map<string, DailyScoutReviewItem>, item: DailyScoutReviewItem | null) {
  if (!item?.job_id) return;
  const existing = map.get(item.job_id);
  if (!existing || (item.total_score ?? 0) > (existing.total_score ?? 0)) {
    map.set(item.job_id, item);
  }
}

function fromTopRecommendation(job: RemoteDiscoveryTopRecommendation): DailyScoutReviewItem | null {
  if (!job.job_id) return null;
  return {
    job_id: job.job_id,
    title: job.title ?? "Untitled job",
    company_name: job.company_name ?? null,
    remote_eligibility: job.remote_eligibility ?? null,
    match_tier: job.match_tier ?? null,
    eligibility_status: job.eligibility_status ?? null,
    total_score: numberValue(job.total_score),
    eligibility_reason: job.eligibility_reason ?? null,
    salary_min: job.salary_min,
    salary_max: job.salary_max,
    salary_currency: job.salary_currency,
    job_url: job.job_url,
    apply_url: job.apply_url,
    review_status: "unreviewed",
    created_from: "top_recommendations",
    raw: job,
  };
}

function fromFallbackRecommendation(job: RecommendedJobMatch): DailyScoutReviewItem {
  return {
    job_id: job.job_id,
    title: job.title,
    company_name: job.company_name ?? null,
    company_id: job.company_id,
    source_platform: undefined,
    remote_eligibility: job.remote_eligibility,
    match_tier: job.match_tier,
    eligibility_status: job.eligibility_status,
    total_score: numberValue(job.total_score),
    eligibility_reason: job.eligibility_reason ?? null,
    salary_min: job.salary_min,
    salary_max: job.salary_max,
    salary_currency: job.salary_currency,
    job_url: job.job_url,
    apply_url: job.apply_url,
    review_status: "unreviewed",
    created_from: "fallback_recommendations",
    raw: job,
  };
}

function recommendedSort(a: DailyScoutReviewItem, b: DailyScoutReviewItem) {
  return (
    eligibilityRank(a.eligibility_status) - eligibilityRank(b.eligibility_status) ||
    tierRank(a.match_tier) - tierRank(b.match_tier) ||
    (b.total_score ?? 0) - (a.total_score ?? 0)
  );
}

function eligibilityRank(value?: string | null) {
  const status = String(value ?? "").toLowerCase();
  if (status === "eligible") return 0;
  if (status === "stretch") return 2;
  if (status === "uncertain") return 3;
  if (status === "unsuitable") return 9;
  return 4;
}

function tierRank(value?: string | null) {
  const tier = String(value ?? "").toLowerCase();
  if (tier === "best_match" || tier === "best") return 0;
  if (tier === "strong_match") return 1;
  if (tier === "worth_checking") return 2;
  if (tier === "stretch") return 3;
  if (tier === "unsuitable") return 9;
  return 4;
}

function isHiddenByDefault(item: DailyScoutReviewItem) {
  const decisionStatus = String(item.decision_status ?? "").toLowerCase();
  return (
    String(item.eligibility_status ?? "").toLowerCase() === "unsuitable" ||
    String(item.match_tier ?? "").toLowerCase() === "unsuitable" ||
    ["skipped", "not_interested", "archived"].includes(decisionStatus) ||
    ["skipped", "not_interested"].includes(item.review_status)
  );
}

function decisionReviewStatus(status?: string | null): DailyScoutReviewStatus | null {
  if (!status || status === "archived") return null;
  if (status === "needs_custom_resume") return "needs_custom_resume";
  if (status === "needs_cold_dm") return "needs_cold_dm";
  if (status === "not_interested") return "not_interested";
  if (status === "applied") return "applied";
  if (status === "skipped") return "skipped";
  if (status === "interested") return "interested";
  if (status === "saved") return "saved";
  return "saved";
}

function decisionStatusValue(decision?: JobApplicationDecisionResponse | JobDecisionListItem | null) {
  return decision?.decision_status ?? decision?.status ?? null;
}

function isReviewState(value: unknown): value is DailyScoutReviewState {
  if (!value || typeof value !== "object") return false;
  const state = value as DailyScoutReviewState;
  return typeof state.job_id === "string" && typeof state.review_status === "string";
}

function numberValue(value: unknown) {
  if (typeof value === "number" && Number.isFinite(value)) return value;
  if (typeof value === "string" && value.trim()) {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : null;
  }
  return null;
}
