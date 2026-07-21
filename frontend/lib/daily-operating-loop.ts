import type { ApplicationCommandCenterModel } from "@/lib/application-command-center";

export type DailyOperatingLoopStatus = "not_started" | "in_progress" | "completed";
export type DailyOperatingLoopStepStatus = "pending" | "current" | "completed" | "skipped";

export type DailyOperatingLoopState = {
  date: string;
  status: DailyOperatingLoopStatus;
  currentStepId: DailyOperatingLoopStepId;
  completedStepIds: DailyOperatingLoopStepId[];
  skippedStepIds: DailyOperatingLoopStepId[];
  startedAt?: string | null;
  completedAt?: string | null;
  notes?: string | null;
  counters?: Record<string, number>;
  lastUpdatedAt?: string | null;
};

export type DailyOperatingLoopStepId =
  | "check_followups"
  | "run_daily_scout"
  | "review_jobs"
  | "rank_with_resume"
  | "prepare_applications"
  | "draft_cold_dms"
  | "update_pipeline"
  | "review_watchlist"
  | "daily_summary";

export type DailyOperatingLoopStep = {
  id: DailyOperatingLoopStepId;
  title: string;
  description: string;
  status: DailyOperatingLoopStepStatus;
  priority: "high" | "medium" | "low";
  estimatedAction: string;
  primaryActionLabel: string;
  secondaryActionLabel?: string;
  href: string;
  count: number;
  isRequired: boolean;
  dependsOn?: DailyOperatingLoopStepId[];
  completionRule: string;
};

export type DailyOperatingLoopModel = {
  date: string;
  state: DailyOperatingLoopState;
  steps: DailyOperatingLoopStep[];
  currentStep: DailyOperatingLoopStep;
  progress: {
    completed: number;
    skipped: number;
    total: number;
    percent: number;
  };
  summary: {
    followUpsDue: number;
    overdueFollowUps: number;
    jobsToReview: number;
    resumeTasks: number;
    coldDmTasks: number;
    applicationsInProgress: number;
    companiesWatched: number;
    discoveryStatus: string;
  };
  warnings: string[];
};

export const dailyOperatingLoopStorageKey = "scoutai.dailyOperatingLoop.v1";

const stepOrder: DailyOperatingLoopStepId[] = [
  "check_followups",
  "run_daily_scout",
  "review_jobs",
  "rank_with_resume",
  "prepare_applications",
  "draft_cold_dms",
  "update_pipeline",
  "review_watchlist",
  "daily_summary",
];

export const dailyOperatingLoopStorage = {
  getAllLoops,
  getTodayLoop,
  saveTodayLoop,
  updateTodayLoop,
  markStepComplete,
  markStepSkipped,
  resetTodayLoop,
  completeTodayLoop,
};

export function localDateKey(date = new Date()) {
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${date.getFullYear()}-${month}-${day}`;
}

export function createDailyLoop(date = localDateKey()): DailyOperatingLoopState {
  const now = new Date().toISOString();
  return {
    date,
    status: "in_progress",
    currentStepId: "check_followups",
    completedStepIds: [],
    skippedStepIds: [],
    startedAt: now,
    completedAt: null,
    notes: "",
    counters: {},
    lastUpdatedAt: now,
  };
}

export function getAllLoops() {
  return Object.values(readLoops()).sort((a, b) => String(b.date).localeCompare(String(a.date)));
}

export function getTodayLoop(date = localDateKey()) {
  const all = readLoops();
  return all[date] ?? null;
}

export function saveTodayLoop(loop: DailyOperatingLoopState) {
  const all = readLoops();
  all[loop.date] = sanitizeLoop(loop);
  return persist(all, all[loop.date]);
}

export function updateTodayLoop(date = localDateKey(), changes: Partial<DailyOperatingLoopState>) {
  const existing = getTodayLoop(date) ?? createDailyLoop(date);
  return saveTodayLoop({ ...existing, ...changes, date, lastUpdatedAt: new Date().toISOString() });
}

export function markStepComplete(date = localDateKey(), stepId: DailyOperatingLoopStepId) {
  const loop = getTodayLoop(date) ?? createDailyLoop(date);
  const completed = unique([...loop.completedStepIds, stepId]);
  const skipped = loop.skippedStepIds.filter((id) => id !== stepId);
  const currentStepId = nextStepId(completed, skipped);
  return saveTodayLoop({
    ...loop,
    status: currentStepId === "daily_summary" && stepId === "daily_summary" ? "completed" : "in_progress",
    currentStepId,
    completedStepIds: completed,
    skippedStepIds: skipped,
    completedAt: stepId === "daily_summary" ? new Date().toISOString() : loop.completedAt ?? null,
    lastUpdatedAt: new Date().toISOString(),
  });
}

export function markStepSkipped(date = localDateKey(), stepId: DailyOperatingLoopStepId) {
  const loop = getTodayLoop(date) ?? createDailyLoop(date);
  const skipped = unique([...loop.skippedStepIds, stepId]);
  const completed = loop.completedStepIds.filter((id) => id !== stepId);
  return saveTodayLoop({
    ...loop,
    status: "in_progress",
    currentStepId: nextStepId(completed, skipped),
    completedStepIds: completed,
    skippedStepIds: skipped,
    lastUpdatedAt: new Date().toISOString(),
  });
}

export function resetTodayLoop(date = localDateKey()) {
  const all = readLoops();
  delete all[date];
  return persist(all, null);
}

export function completeTodayLoop(date = localDateKey()) {
  const loop = getTodayLoop(date) ?? createDailyLoop(date);
  return saveTodayLoop({
    ...loop,
    status: "completed",
    currentStepId: "daily_summary",
    completedStepIds: stepOrder,
    skippedStepIds: [],
    completedAt: new Date().toISOString(),
    lastUpdatedAt: new Date().toISOString(),
  });
}

export function buildDailyOperatingLoopModel(
  commandCenterModel: ApplicationCommandCenterModel,
  existingLoop: DailyOperatingLoopState | null,
  now = new Date(),
): DailyOperatingLoopModel {
  const date = localDateKey(now);
  const state = existingLoop ?? {
    ...createDailyLoop(date),
    status: "not_started" as const,
    startedAt: null,
  };
  const noActiveResume = commandCenterModel.summary.activeResume === "No active resume";
  const discoveryToday = !commandCenterModel.warnings.some((warning) => /No Daily Scout run/i.test(warning));
  const steps: DailyOperatingLoopStep[] = [
    step("check_followups", "Check follow-ups", "Handle overdue, due-today, and copied/drafted outreach before creating new work.", commandCenterModel.summary.overdueFollowUps + commandCenterModel.summary.followUpsDue + copiedOrDraftedCount(commandCenterModel), "high", "Open Follow-up Tracker", "/applications/follow-ups", "Complete after due outreach has been handled.", true),
    step("run_daily_scout", "Run or review Daily Scout", discoveryToday ? "A discovery run exists for today. Review it if needed." : "Run Daily Scout before reviewing fresh opportunities.", discoveryToday ? 0 : 1, discoveryToday ? "low" : "high", "Open Discovery Control Center", "/discovery/control-center", "Complete after today's run is done or reviewed.", !discoveryToday),
    step("review_jobs", "Review new jobs", "Triage recommended jobs and save, skip, or route them to resume/cold DM work.", commandCenterModel.summary.jobsToReview, "medium", "Open Review Queue", "/discovery/control-center#review-queue", "Complete after today's new jobs are triaged.", commandCenterModel.summary.jobsToReview > 0, ["run_daily_scout"]),
    step("rank_with_resume", "Rank jobs with active resume", noActiveResume ? "No active resume found. You can skip this or upload a resume first." : "Use Rank with Resume on the review queue for the best visible jobs.", noActiveResume ? 0 : commandCenterModel.summary.jobsToReview, noActiveResume ? "low" : "medium", "Open Review Queue", "/discovery/control-center#review-queue", "Complete after top jobs have resume-aware ranking.", !noActiveResume && commandCenterModel.summary.jobsToReview > 0, ["review_jobs"]),
    step("prepare_applications", "Prepare application materials", "Open workspaces for interested, strong-fit, or resume-task jobs and generate materials as needed.", commandCenterModel.summary.resumeTasks + commandCenterModel.summary.applicationsInProgress, "medium", "Open Pipeline", "/jobs/pipeline", "Complete after key application materials are prepared.", commandCenterModel.summary.resumeTasks > 0, ["rank_with_resume"]),
    step("draft_cold_dms", "Draft cold DMs", "Create or update cold outreach drafts for roles that need a human touch.", commandCenterModel.summary.coldDmTasks, "medium", "Open Cold DM tasks", "/applications/command-center#cold-dm-tasks", "Complete after drafts are prepared or intentionally skipped.", commandCenterModel.summary.coldDmTasks > 0, ["prepare_applications"]),
    step("update_pipeline", "Update pipeline", "Keep saved, interested, applied, and interviewing statuses current.", commandCenterModel.summary.applicationsInProgress + commandCenterModel.summary.resumeTasks + commandCenterModel.summary.coldDmTasks, "medium", "Open Pipeline", "/jobs/pipeline", "Complete after today's status changes are reflected.", commandCenterModel.summary.applicationsInProgress > 0, ["draft_cold_dms"]),
    step("review_watchlist", "Review watchlist", "Check watched companies and related jobs.", commandCenterModel.summary.companiesWatched, "low", "Open Company Watchlist", "/companies/watchlist", "Complete after relevant watched companies are checked.", false),
    step("daily_summary", "Daily summary", "Review what changed today and export a Markdown summary.", 1, "low", "View Summary", "/applications/command-center#daily-summary", "Complete to close today's loop.", true),
  ].map((item) => ({
    ...item,
    status: !item.isRequired && item.count === 0 ? "completed" as const : stepStatus(item.id, state),
  }));
  const currentStep = steps.find((item) => item.id === state.currentStepId && item.status !== "completed" && item.status !== "skipped") ??
    steps.find((item) => item.status === "pending") ??
    steps[steps.length - 1];
  const completed = steps.filter((step) => step.status === "completed").length;
  const skipped = steps.filter((step) => step.status === "skipped").length;
  return {
    date,
    state,
    steps,
    currentStep,
    progress: {
      completed,
      skipped,
      total: steps.length,
      percent: Math.round(((completed + skipped) / steps.length) * 100),
    },
    summary: {
      followUpsDue: commandCenterModel.summary.followUpsDue,
      overdueFollowUps: commandCenterModel.summary.overdueFollowUps,
      jobsToReview: commandCenterModel.summary.jobsToReview,
      resumeTasks: commandCenterModel.summary.resumeTasks,
      coldDmTasks: commandCenterModel.summary.coldDmTasks,
      applicationsInProgress: commandCenterModel.summary.applicationsInProgress,
      companiesWatched: commandCenterModel.summary.companiesWatched,
      discoveryStatus: String(commandCenterModel.latestDiscoveryRun?.status ?? "not_run_today"),
    },
    warnings: noActiveResume ? ["No active resume found. You can skip resume ranking or upload a resume first."] : [],
  };
}

export function buildDailyOperatingLoopMarkdown(model: DailyOperatingLoopModel) {
  const completed = model.steps.filter((step) => step.status === "completed");
  const skipped = model.steps.filter((step) => step.status === "skipped");
  return [
    `# ScoutAI Daily Job Search Summary - ${model.date}`,
    "",
    "## Completed Steps",
    ...(completed.length ? completed.map((step) => `- ${step.title}`) : ["- None yet"]),
    "",
    "## Skipped Steps",
    ...(skipped.length ? skipped.map((step) => `- ${step.title}`) : ["- None"]),
    "",
    "## Follow-ups",
    `- Due: ${model.summary.followUpsDue}`,
    `- Overdue remaining: ${model.summary.overdueFollowUps}`,
    "",
    "## Jobs Reviewed",
    `- Jobs to review remaining: ${model.summary.jobsToReview}`,
    "",
    "## Resume Tasks",
    `- Resume tasks remaining: ${model.summary.resumeTasks}`,
    "",
    "## Cold DM Tasks",
    `- Cold DM tasks remaining: ${model.summary.coldDmTasks}`,
    "",
    "## Applications",
    `- Applications in progress: ${model.summary.applicationsInProgress}`,
    "",
    "## Watchlist",
    `- Companies watched: ${model.summary.companiesWatched}`,
    "",
    "## Discovery",
    `- Latest status: ${model.summary.discoveryStatus}`,
    "",
    "## Notes",
    model.state.notes?.trim() || "No notes.",
    "",
  ].join("\n");
}

function step(
  id: DailyOperatingLoopStepId,
  title: string,
  description: string,
  count: number,
  priority: DailyOperatingLoopStep["priority"],
  primaryActionLabel: string,
  href: string,
  completionRule: string,
  isRequired: boolean,
  dependsOn: DailyOperatingLoopStepId[] = [],
): DailyOperatingLoopStep {
  return {
    id,
    title,
    description,
    count,
    priority,
    primaryActionLabel,
    secondaryActionLabel: "Mark as already done",
    href,
    isRequired,
    dependsOn,
    estimatedAction: count > 0 ? `${count} item${count === 1 ? "" : "s"}` : "No active items",
    completionRule,
    status: "pending",
  };
}

function stepStatus(id: DailyOperatingLoopStepId, state: DailyOperatingLoopState): DailyOperatingLoopStepStatus {
  if (state.completedStepIds.includes(id)) return "completed";
  if (state.skippedStepIds.includes(id)) return "skipped";
  if (state.currentStepId === id && state.status !== "completed") return "current";
  return "pending";
}

function nextStepId(completed: DailyOperatingLoopStepId[], skipped: DailyOperatingLoopStepId[]): DailyOperatingLoopStepId {
  return stepOrder.find((id) => !completed.includes(id) && !skipped.includes(id)) ?? "daily_summary";
}

function copiedOrDraftedCount(model: ApplicationCommandCenterModel) {
  return model.coldDmTasks.filter((task) => task.status === "copied" || task.status === "drafted").length;
}

function readLoops(): Record<string, DailyOperatingLoopState> {
  if (typeof window === "undefined") return {};
  try {
    const raw = window.localStorage.getItem(dailyOperatingLoopStorageKey);
    if (!raw) return {};
    const parsed = JSON.parse(raw);
    if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) return {};
    const entries = Object.entries(parsed).filter(([, value]) => isLoop(value));
    return Object.fromEntries(entries) as Record<string, DailyOperatingLoopState>;
  } catch {
    return {};
  }
}

function persist(all: Record<string, DailyOperatingLoopState>, loop: DailyOperatingLoopState | null) {
  try {
    window.localStorage.setItem(dailyOperatingLoopStorageKey, JSON.stringify(all));
    return { ok: true, loop };
  } catch {
    return { ok: false, error: "Could not save daily loop locally.", loop };
  }
}

function sanitizeLoop(loop: DailyOperatingLoopState): DailyOperatingLoopState {
  return {
    ...loop,
    completedStepIds: loop.completedStepIds.filter((id) => stepOrder.includes(id)),
    skippedStepIds: loop.skippedStepIds.filter((id) => stepOrder.includes(id)),
  };
}

function isLoop(value: unknown): value is DailyOperatingLoopState {
  if (!value || typeof value !== "object") return false;
  const record = value as Record<string, unknown>;
  return typeof record.date === "string" && typeof record.status === "string" && typeof record.currentStepId === "string";
}

function unique<T>(values: T[]) {
  return Array.from(new Set(values));
}
