import type { ColdDmDraftResult, SavedColdDmDraft } from "@/lib/cold-dm-draft";
import type { DailyScoutReviewItem } from "@/lib/daily-scout-review-queue";
import type { JobDecisionStatus } from "@/types/job-decision";

export type ApplicationOutreachType =
  | "founder_dm"
  | "recruiter_dm"
  | "hiring_manager_dm"
  | "team_member_dm"
  | "twitter_dm"
  | "linkedin_note"
  | "email_follow_up"
  | "application_follow_up"
  | "other";

export type ApplicationOutreachStatus =
  | "drafted"
  | "copied"
  | "sent_manually"
  | "follow_up_due"
  | "follow_up_sent"
  | "no_response"
  | "responded"
  | "closed";

export type ApplicationFollowUpItem = {
  id: string;
  job_id: string;
  company_name?: string | null;
  job_title?: string | null;
  source_platform?: string | null;
  job_url?: string | null;
  apply_url?: string | null;
  workspace_url?: string | null;
  outreach_type: ApplicationOutreachType;
  outreach_status: ApplicationOutreachStatus;
  draft_id?: string | null;
  draft_preview?: string | null;
  message_target?: string | null;
  sent_at?: string | null;
  follow_up_due_at?: string | null;
  follow_up_sent_at?: string | null;
  last_action_at?: string | null;
  notes?: string | null;
  decision_status?: JobDecisionStatus | null;
  created_at: string;
  updated_at: string;
};

export type FollowUpDashboard = {
  total: number;
  drafted: number;
  copied: number;
  sentManually: number;
  dueToday: number;
  overdue: number;
  upcoming: number;
  responded: number;
  noResponse: number;
  closed: number;
  needsAction: number;
  byStatus: Record<string, number>;
  byType: Record<string, number>;
};

export const applicationFollowUpStorageKey = "scoutai.applicationFollowUps.v1";

const terminalStatuses = new Set<ApplicationOutreachStatus>(["follow_up_sent", "responded", "closed"]);

export const outreachTypeOptions: Array<{ value: ApplicationOutreachType; label: string }> = [
  { value: "founder_dm", label: "Founder DM" },
  { value: "recruiter_dm", label: "Recruiter DM" },
  { value: "hiring_manager_dm", label: "Hiring Manager DM" },
  { value: "team_member_dm", label: "Team Member DM" },
  { value: "twitter_dm", label: "X/Twitter DM" },
  { value: "linkedin_note", label: "LinkedIn Note" },
  { value: "email_follow_up", label: "Email Follow-up" },
  { value: "application_follow_up", label: "Application Follow-up" },
  { value: "other", label: "Other" },
];

export const outreachStatusOptions: Array<{ value: ApplicationOutreachStatus; label: string }> = [
  { value: "drafted", label: "Drafted" },
  { value: "copied", label: "Copied" },
  { value: "sent_manually", label: "Sent Manually" },
  { value: "follow_up_due", label: "Follow-up Due" },
  { value: "follow_up_sent", label: "Follow-up Sent" },
  { value: "no_response", label: "No Response" },
  { value: "responded", label: "Responded" },
  { value: "closed", label: "Closed" },
];

export const applicationFollowUpStorage = {
  getFollowUps,
  getFollowUpsForJob,
  saveFollowUp,
  updateFollowUp,
  deleteFollowUp,
  upsertFollowUpForJob,
  markDrafted,
  markCopied,
  markSentManually,
  markFollowUpSent,
  markResponded,
  markNoResponse,
  markClosed,
};

export function getFollowUps(): ApplicationFollowUpItem[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = window.localStorage.getItem(applicationFollowUpStorageKey);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed.filter(isFollowUpItem) : [];
  } catch {
    return [];
  }
}

export function getFollowUpsForJob(jobId: string) {
  return getFollowUps().filter((item) => item.job_id === jobId);
}

export function saveFollowUp(item: Partial<ApplicationFollowUpItem> & { job_id: string }) {
  const now = new Date().toISOString();
  const nextItem: ApplicationFollowUpItem = {
    id: item.id ?? makeId(item.job_id),
    job_id: item.job_id,
    company_name: item.company_name ?? null,
    job_title: item.job_title ?? null,
    source_platform: item.source_platform ?? null,
    job_url: item.job_url ?? null,
    apply_url: item.apply_url ?? null,
    workspace_url: item.workspace_url ?? `/jobs/${item.job_id}/workspace`,
    outreach_type: item.outreach_type ?? "other",
    outreach_status: item.outreach_status ?? "drafted",
    draft_id: item.draft_id ?? null,
    draft_preview: preview(item.draft_preview),
    message_target: item.message_target ?? null,
    sent_at: item.sent_at ?? null,
    follow_up_due_at: item.follow_up_due_at ?? null,
    follow_up_sent_at: item.follow_up_sent_at ?? null,
    last_action_at: item.last_action_at ?? now,
    notes: item.notes ?? null,
    decision_status: item.decision_status ?? null,
    created_at: item.created_at ?? now,
    updated_at: now,
  };
  const next = [nextItem, ...getFollowUps().filter((existing) => existing.id !== nextItem.id)];
  return persist(next, nextItem);
}

export function updateFollowUp(id: string, changes: Partial<ApplicationFollowUpItem>) {
  const now = new Date().toISOString();
  let updated: ApplicationFollowUpItem | null = null;
  const next = getFollowUps().map((item) => {
    if (item.id !== id) return item;
    updated = {
      ...item,
      ...changes,
      draft_preview: changes.draft_preview !== undefined ? preview(changes.draft_preview) : item.draft_preview,
      updated_at: now,
      last_action_at: changes.last_action_at ?? now,
    };
    return updated;
  });
  return persist(next, updated);
}

export function deleteFollowUp(id: string) {
  return persist(getFollowUps().filter((item) => item.id !== id), null);
}

export function upsertFollowUpForJob(jobId: string, item: Partial<ApplicationFollowUpItem>) {
  const existing = getFollowUps().find((candidate) => candidate.job_id === jobId && candidate.draft_id === item.draft_id) ??
    getFollowUps().find((candidate) => candidate.job_id === jobId && candidate.outreach_type === item.outreach_type);
  if (existing) return updateFollowUp(existing.id, item);
  return saveFollowUp({ ...item, job_id: jobId });
}

export function markDrafted(jobId: string, draftData: FollowUpDraftData, reviewItem?: DailyScoutReviewItem) {
  return upsertFollowUpForJob(jobId, buildDraftFollowUp(jobId, "drafted", draftData, reviewItem));
}

export function markCopied(jobId: string, draftData: FollowUpDraftData, reviewItem?: DailyScoutReviewItem) {
  return upsertFollowUpForJob(jobId, buildDraftFollowUp(jobId, "copied", draftData, reviewItem));
}

export function markSentManually(jobId: string, sentAt = new Date().toISOString(), followUpDueAt?: string | null) {
  return upsertFollowUpForJob(jobId, {
    outreach_status: "sent_manually",
    sent_at: sentAt,
    follow_up_due_at: followUpDueAt ?? addDaysLocalIso(sentAt, 3),
  });
}

export function markFollowUpSent(id: string, followUpSentAt = new Date().toISOString()) {
  return updateFollowUp(id, { outreach_status: "follow_up_sent", follow_up_sent_at: followUpSentAt });
}

export function markResponded(id: string) {
  return updateFollowUp(id, { outreach_status: "responded" });
}

export function markNoResponse(id: string) {
  return updateFollowUp(id, { outreach_status: "no_response" });
}

export function markClosed(id: string) {
  return updateFollowUp(id, { outreach_status: "closed" });
}

export type FollowUpDraftData = {
  draft?: ColdDmDraftResult | SavedColdDmDraft | null;
  outreach_type?: ApplicationOutreachType;
  message_target?: string | null;
  body?: string | null;
};

export function buildFollowUpDashboard(items: ApplicationFollowUpItem[], now = new Date()): FollowUpDashboard {
  const dashboard: FollowUpDashboard = {
    total: items.length,
    drafted: 0,
    copied: 0,
    sentManually: 0,
    dueToday: 0,
    overdue: 0,
    upcoming: 0,
    responded: 0,
    noResponse: 0,
    closed: 0,
    needsAction: 0,
    byStatus: {},
    byType: {},
  };
  for (const item of items) {
    dashboard.byStatus[item.outreach_status] = (dashboard.byStatus[item.outreach_status] ?? 0) + 1;
    dashboard.byType[item.outreach_type] = (dashboard.byType[item.outreach_type] ?? 0) + 1;
    if (item.outreach_status === "drafted") dashboard.drafted += 1;
    if (item.outreach_status === "copied") dashboard.copied += 1;
    if (item.outreach_status === "sent_manually") dashboard.sentManually += 1;
    if (item.outreach_status === "responded") dashboard.responded += 1;
    if (item.outreach_status === "no_response") dashboard.noResponse += 1;
    if (item.outreach_status === "closed") dashboard.closed += 1;
    const dueState = dueDateState(item, now);
    if (dueState === "overdue") dashboard.overdue += 1;
    if (dueState === "due_today") dashboard.dueToday += 1;
    if (dueState === "upcoming") dashboard.upcoming += 1;
    if (needsAction(item, now)) dashboard.needsAction += 1;
  }
  return dashboard;
}

export function needsAction(item: ApplicationFollowUpItem, now = new Date()) {
  if (terminalStatuses.has(item.outreach_status)) return false;
  if (item.outreach_status === "drafted" || item.outreach_status === "copied") return true;
  const dueState = dueDateState(item, now);
  return dueState === "overdue" || dueState === "due_today" || item.outreach_status === "follow_up_due";
}

export function dueDateState(item: ApplicationFollowUpItem, now = new Date()) {
  if (!item.follow_up_due_at || terminalStatuses.has(item.outreach_status)) return "none";
  const due = parseDate(item.follow_up_due_at);
  if (!due) return "none";
  const dueStart = localDayStart(due).getTime();
  const nowStart = localDayStart(now).getTime();
  if (dueStart < nowStart) return "overdue";
  if (dueStart === nowStart) return "due_today";
  return "upcoming";
}

export function outreachTypeFromDraftTarget(value?: string | null): ApplicationOutreachType {
  if (value === "founder") return "founder_dm";
  if (value === "recruiter") return "recruiter_dm";
  if (value === "hiring_manager") return "hiring_manager_dm";
  if (value === "team_member") return "team_member_dm";
  if (value === "twitter_dm") return "twitter_dm";
  if (value === "linkedin_connection") return "linkedin_note";
  if (value === "follow_up") return "application_follow_up";
  return "other";
}

function buildDraftFollowUp(
  jobId: string,
  status: ApplicationOutreachStatus,
  draftData: FollowUpDraftData,
  reviewItem?: DailyScoutReviewItem,
) {
  const draft = draftData.draft;
  return {
    job_id: jobId,
    company_name: reviewItem?.company_name ?? null,
    job_title: reviewItem?.title ?? null,
    source_platform: reviewItem?.source_platform ?? reviewItem?.source_name ?? null,
    job_url: reviewItem?.job_url ?? null,
    apply_url: reviewItem?.apply_url ?? null,
    workspace_url: `/jobs/${jobId}/workspace`,
    outreach_type: draftData.outreach_type ?? outreachTypeFromDraftTarget(draft?.targetType),
    outreach_status: status,
    draft_id: draft?.id ?? null,
    draft_preview: draftData.body ?? draft?.body ?? null,
    message_target: draftData.message_target ?? null,
    decision_status: reviewItem?.decision_status ?? null,
  };
}

function persist(items: ApplicationFollowUpItem[], changed: ApplicationFollowUpItem | null) {
  try {
    window.localStorage.setItem(applicationFollowUpStorageKey, JSON.stringify(items));
    return { ok: true, item: changed, items };
  } catch {
    return { ok: false, error: "Could not save follow-up data locally.", item: changed, items: getFollowUps() };
  }
}

function isFollowUpItem(value: unknown): value is ApplicationFollowUpItem {
  if (!value || typeof value !== "object") return false;
  const record = value as Record<string, unknown>;
  return typeof record.id === "string" && typeof record.job_id === "string" && typeof record.outreach_status === "string";
}

function makeId(jobId: string) {
  return `follow-up-${jobId || "job"}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

function preview(value?: string | null) {
  if (!value) return null;
  return value.replace(/\s+/g, " ").trim().slice(0, 200);
}

function addDaysLocalIso(value: string, days: number) {
  const date = parseDate(value) ?? new Date();
  date.setDate(date.getDate() + days);
  return date.toISOString();
}

function parseDate(value: string) {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? null : date;
}

function localDayStart(date: Date) {
  return new Date(date.getFullYear(), date.getMonth(), date.getDate());
}
