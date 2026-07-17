import type { JobDecisionListItem, JobDecisionStatus } from "@/types/job-decision";

export type PipelineActionItem = {
  decision: JobDecisionListItem;
  reason: string;
  score: number;
};

export type PipelineConversionSummary = {
  applied_rate: number;
  interview_rate: number;
  offer_rate: number;
  rejection_rate: number;
  applied_label: string;
  interview_label: string;
  offer_label: string;
  rejection_label: string;
};

export type ApplicationPipelineAnalytics = {
  total_tracked: number;
  active_total: number;
  archived_total: number;
  saved_count: number;
  interested_count: number;
  needs_resume_count: number;
  needs_cold_dm_count: number;
  applied_count: number;
  interviewing_count: number;
  rejected_count: number;
  offer_count: number;
  skipped_count: number;
  not_interested_count: number;
  archived_count: number;
  high_priority_count: number;
  medium_priority_count: number;
  low_priority_count: number;
  urgent_priority_count: number;
  best_match_count: number;
  strong_match_count: number;
  worth_checking_count: number;
  stretch_count: number;
  jobs_ready_to_apply: number;
  jobs_needing_action: number;
  stale_applications: number;
  conversion_summary: PipelineConversionSummary;
  priority_breakdown: Array<{ label: string; value: number }>;
  match_tier_breakdown: Array<{ label: string; value: number }>;
  status_breakdown: Array<{ label: string; value: number }>;
  needs_action_items: PipelineActionItem[];
};

const activeStatuses = new Set([
  "saved",
  "interested",
  "needs_custom_resume",
  "needs_cold_dm",
  "applied",
  "interviewing",
  "rejected",
  "offer",
]);
const inactiveStatuses = new Set(["archived", "skipped", "not_interested", "dismissed"]);
const readyStatuses = new Set(["interested", "needs_custom_resume", "needs_cold_dm"]);
const staleAfterMs = 14 * 24 * 60 * 60 * 1000;

export function buildApplicationPipelineAnalytics(
  decisions: JobDecisionListItem[] = [],
  now = new Date(),
): ApplicationPipelineAnalytics {
  const base: ApplicationPipelineAnalytics = {
    total_tracked: decisions.length,
    active_total: 0,
    archived_total: 0,
    saved_count: 0,
    interested_count: 0,
    needs_resume_count: 0,
    needs_cold_dm_count: 0,
    applied_count: 0,
    interviewing_count: 0,
    rejected_count: 0,
    offer_count: 0,
    skipped_count: 0,
    not_interested_count: 0,
    archived_count: 0,
    high_priority_count: 0,
    medium_priority_count: 0,
    low_priority_count: 0,
    urgent_priority_count: 0,
    best_match_count: 0,
    strong_match_count: 0,
    worth_checking_count: 0,
    stretch_count: 0,
    jobs_ready_to_apply: 0,
    jobs_needing_action: 0,
    stale_applications: 0,
    conversion_summary: conversionSummary(0, 0, 0, 0, 0),
    priority_breakdown: [],
    match_tier_breakdown: [],
    status_breakdown: [],
    needs_action_items: [],
  };

  const priorities: Record<string, number> = {};
  const tiers: Record<string, number> = {};
  const statuses: Record<string, number> = {};
  const actionItems: PipelineActionItem[] = [];

  for (const decision of decisions) {
    const status = statusOf(decision);
    const priority = decision.priority ?? "medium";
    const tier = decision.match_tier ?? "unscored";

    statuses[status] = (statuses[status] ?? 0) + 1;
    priorities[priority] = (priorities[priority] ?? 0) + 1;
    tiers[tier] = (tiers[tier] ?? 0) + 1;

    if (activeStatuses.has(status)) base.active_total += 1;
    if (inactiveStatuses.has(status)) base.archived_total += 1;
    if (status === "saved") base.saved_count += 1;
    if (status === "interested") base.interested_count += 1;
    if (status === "needs_custom_resume") base.needs_resume_count += 1;
    if (status === "needs_cold_dm") base.needs_cold_dm_count += 1;
    if (status === "applied") base.applied_count += 1;
    if (status === "interviewing") base.interviewing_count += 1;
    if (status === "rejected") base.rejected_count += 1;
    if (status === "offer") base.offer_count += 1;
    if (status === "skipped" || status === "dismissed") base.skipped_count += 1;
    if (status === "not_interested") base.not_interested_count += 1;
    if (status === "archived") base.archived_count += 1;

    if (priority === "urgent") base.urgent_priority_count += 1;
    if (priority === "high") base.high_priority_count += 1;
    if (priority === "medium") base.medium_priority_count += 1;
    if (priority === "low") base.low_priority_count += 1;

    if (tier === "best_match") base.best_match_count += 1;
    if (tier === "strong_match") base.strong_match_count += 1;
    if (tier === "worth_checking") base.worth_checking_count += 1;
    if (tier === "stretch") base.stretch_count += 1;

    if (isReadyToApply(decision, status)) {
      base.jobs_ready_to_apply += 1;
    }

    const stale = isStaleApplication(decision, status, now);
    if (stale) {
      base.stale_applications += 1;
    }

    const reason = actionReason(decision, status, stale);
    if (reason) {
      base.jobs_needing_action += 1;
      actionItems.push({ decision, reason, score: actionScore(decision, status, stale) });
    }
  }

  base.conversion_summary = conversionSummary(
    base.active_total,
    base.applied_count,
    base.interviewing_count,
    base.offer_count,
    base.rejected_count,
  );
  base.priority_breakdown = toBreakdown(priorities, ["urgent", "high", "medium", "low"]);
  base.match_tier_breakdown = toBreakdown(tiers, [
    "best_match",
    "strong_match",
    "worth_checking",
    "stretch",
    "unscored",
  ]);
  base.status_breakdown = toBreakdown(statuses, [
    "saved",
    "interested",
    "needs_custom_resume",
    "needs_cold_dm",
    "applied",
    "interviewing",
    "rejected",
    "offer",
    "archived",
    "skipped",
    "not_interested",
  ]);
  base.needs_action_items = actionItems
    .sort((a, b) => b.score - a.score)
    .slice(0, 5);

  return base;
}

function isReadyToApply(decision: JobDecisionListItem, status: string) {
  return readyStatuses.has(status) && Boolean(decision.apply_url ?? decision.job_url);
}

function isStaleApplication(decision: JobDecisionListItem, status: string, now: Date) {
  if (status !== "applied") {
    return false;
  }
  const value = decision.applied_at ?? decision.updated_at ?? decision.created_at;
  if (!value) {
    return false;
  }
  const timestamp = new Date(value).getTime();
  if (!Number.isFinite(timestamp)) {
    return false;
  }
  return now.getTime() - timestamp > staleAfterMs;
}

function actionReason(decision: JobDecisionListItem, status: string, stale: boolean) {
  if (status === "needs_custom_resume") return "Needs custom resume";
  if (status === "needs_cold_dm") return "Needs cold DM";
  if (stale) return "Applied over 14 days ago";
  if ((status === "saved" || status === "interested") && highPriority(decision.priority)) {
    return `High-priority ${status} job`;
  }
  if (
    (status === "interested" || status === "needs_custom_resume" || status === "needs_cold_dm") &&
    "next_action" in decision &&
    !decision.next_action
  ) {
    return "Missing next action";
  }
  return null;
}

function actionScore(decision: JobDecisionListItem, status: string, stale: boolean) {
  let score = 0;
  if (highPriority(decision.priority)) score += 40;
  if (decision.match_tier === "best_match" || decision.match_tier === "strong_match") score += 25;
  if (status === "needs_custom_resume" || status === "needs_cold_dm") score += 20;
  if (stale) score += 15;
  return score;
}

function highPriority(priority?: string | null) {
  return priority === "high" || priority === "urgent";
}

function statusOf(decision: JobDecisionListItem): JobDecisionStatus {
  return decision.decision_status ?? decision.status ?? "saved";
}

function conversionSummary(
  active: number,
  applied: number,
  interviewing: number,
  offer: number,
  rejected: number,
): PipelineConversionSummary {
  return {
    applied_rate: rate(applied, active),
    interview_rate: rate(interviewing, applied),
    offer_rate: rate(offer, applied),
    rejection_rate: rate(rejected, applied),
    applied_label: labelRate(applied, active),
    interview_label: labelRate(interviewing, applied),
    offer_label: labelRate(offer, applied),
    rejection_label: labelRate(rejected, applied),
  };
}

function rate(numerator: number, denominator: number) {
  return denominator > 0 ? Math.round((numerator / denominator) * 100) : 0;
}

function labelRate(numerator: number, denominator: number) {
  return denominator > 0 ? `${rate(numerator, denominator)}%` : "Not enough data";
}

function toBreakdown(values: Record<string, number>, preferredOrder: string[]) {
  const ordered = [
    ...preferredOrder.filter((item) => values[item] != null),
    ...Object.keys(values).filter((item) => !preferredOrder.includes(item)).sort(),
  ];
  return ordered.map((label) => ({ label, value: values[label] ?? 0 }));
}
