import { formatMatchTier, formatRemoteEligibility, formatSalary, normalizeExternalUrl } from "@/components/recommendations/recommendation-format";
import type { DailyScoutReviewItem } from "@/lib/daily-scout-review-queue";
import type { ColdDmDraftResult, SavedColdDmDraft } from "@/lib/cold-dm-draft";
import type { ResumeFitResult } from "@/lib/resume-aware-review-ranking";
import type { ApplicationPacketResponse } from "@/types/application-packet";
import type { ApplicationPrepResponse } from "@/types/application-prep";
import type { CompanyWatchlistResponse } from "@/types/company-watchlist";
import type { JobApplicationDecisionResponse } from "@/types/job-decision";
import type { ResumeResponse } from "@/types/resume";
import type { ResumeImprovementResponse } from "@/types/resume-improvement";

type MarkdownValue = string | number | boolean | null | undefined;

export type ApplicationExportInput = {
  reviewItem: DailyScoutReviewItem;
  activeResume?: ResumeResponse | null;
  resumeFitResult?: ResumeFitResult | null;
  applicationPacket?: ApplicationPacketResponse | null;
  resumeImprovement?: ResumeImprovementResponse | null;
  prepNotes?: ApplicationPrepResponse | null;
  decision?: JobApplicationDecisionResponse | null;
  watchlistItem?: CompanyWatchlistResponse | null;
  coldDmDrafts?: Array<ColdDmDraftResult | SavedColdDmDraft> | null;
  generatedAt?: Date;
  nextAction?: string | null;
};

const blockedKeys = new Set([
  "raw_text",
  "rawText",
  "resume_text",
  "resumeText",
  "full_resume",
  "fullResume",
  "parsed_text",
  "parsedText",
  "storage_path",
  "storagePath",
]);

export function buildApplicationExportMarkdown(input: ApplicationExportInput) {
  const item = input.reviewItem;
  const packet = input.applicationPacket ?? null;
  const improvement = input.resumeImprovement ?? null;
  const prep = input.prepNotes ?? null;
  const fit = input.resumeFitResult ?? reviewItemResumeFit(item);
  const decision = input.decision ?? item.decision ?? null;
  const watchlist = input.watchlistItem ?? null;
  const generatedAt = input.generatedAt ?? new Date();
  const title = cleanInline(item.title) || cleanInline(packet?.title) || cleanInline(prep?.title) || "Untitled Job";
  const company = cleanInline(item.company_name) || cleanInline(packet?.company_name) || cleanInline(prep?.company_name) || "Unknown Company";
  const jobUrl = normalizeLink(item.job_url);
  const applyUrl = normalizeLink(item.apply_url);
  const workspaceUrl = item.job_id ? `/jobs/${item.job_id}/workspace` : null;
  const lines: string[] = [];

  lines.push(`# Application Pack - ${title} at ${company}`);
  lines.push("");
  lines.push(`Generated: ${generatedAt.toISOString()}`);
  lines.push("");

  addBulletSection(lines, "## Job Snapshot", [
    ["Title", title],
    ["Company", company],
    ["Source", item.source_name ?? item.source_platform ?? item.created_from],
    ["Match Tier", formatMatchTier(item.match_tier ?? packet?.match_tier ?? prep?.match_tier ?? "unknown")],
    ["Eligibility", item.eligibility_status],
    ["Score", scoreLabel(item.total_score ?? packet?.total_score ?? prep?.total_score)],
    ["Remote", formatRemoteEligibility(item.remote_eligibility ?? packet?.remote_eligibility ?? prep?.remote_eligibility ?? "unknown")],
    ["Salary", formatSalary({
      salary_min: item.salary_min,
      salary_max: item.salary_max,
      salary_currency: item.salary_currency,
    })],
    ["Active Resume", activeResumeLabel(input.activeResume)],
    ["Job URL", jobUrl],
    ["Apply URL", applyUrl],
    ["Workspace", workspaceUrl],
  ]);

  addParagraphSection(lines, "## Recommended Next Action", input.nextAction ?? prep?.suggested_next_action ?? improvement?.suggested_next_action ?? decision?.next_action ?? null);
  addParagraphSection(lines, "## Match Reason", item.eligibility_reason ?? prep?.fit_summary ?? packet?.resume_match_summary ?? null);

  if (fit) {
    addBulletSection(lines, "## Resume Fit", [
      ["Fit Score", scoreLabel(fit.resume_fit_score)],
      ["Fit Tier", fit.resume_fit_tier],
      ["Summary", fit.resume_fit_summary],
    ]);
    addListSection(lines, "### Strengths", fit.resume_strengths);
    addListSection(lines, "### Gaps", fit.resume_gaps);
    addParagraphSection(lines, "### Suggested Action", fit.resume_action);
  } else {
    addBulletSection(lines, "## Resume Fit", [
      ["Fit Score", null],
      ["Fit Tier", "unknown"],
      ["Summary", packet?.resume_match_summary],
    ]);
    addListSection(lines, "### Strengths", packet?.resume_strengths);
    addListSection(lines, "### Gaps", packet?.resume_gaps);
  }

  addParagraphSection(lines, "## Application Positioning", packet?.application_positioning);
  addListSection(lines, "## Resume Focus", packet?.resume_focus ?? prep?.resume_focus_points);
  addListSection(lines, "## Suggested Resume Bullets", packet?.resume_bullet_suggestions ?? improvement?.bullet_suggestions);
  addListSection(lines, "## Project Evidence", packet?.project_evidence_to_use ?? prep?.project_talking_points);
  addListSection(lines, "## Cover Note Outline", packet?.cover_note_outline?.items);
  addListSection(lines, "## Cold DM Outline", packet?.cold_dm_outline?.items ?? prep?.cold_dm_angle);
  addColdDmDrafts(lines, input.coldDmDrafts);

  if (prepHasContent(prep)) {
    lines.push("## Prep Notes");
    addSubParagraph(lines, "### Fit Summary", prep?.fit_summary);
    addSubList(lines, "### Talking Points", prep?.project_talking_points);
    addSubList(lines, "### Concerns", prep?.concerns);
    addSubList(lines, "### Missing Info", prep?.missing_information);
    addSubParagraph(lines, "### Next Action", prep?.suggested_next_action);
    lines.push("");
  }

  addChecklistSection(lines, "## Checklist", packet?.application_checklist ?? prep?.application_checklist ?? packet?.suggested_apply_plan);
  addListSection(lines, "## Risks", packet?.risks_to_verify ?? improvement?.risks);

  addBulletSection(lines, "## Resume Improvement Suggestions", [
    ["Summary", improvement?.improvement_summary],
    ["Suggested Next Action", improvement?.suggested_next_action],
  ]);
  addListSection(lines, "### Section Suggestions", improvement?.section_suggestions);
  addListSection(lines, "### Skill Gaps", improvement?.skill_gap_suggestions);
  addListSection(lines, "### Project Reordering", improvement?.project_reordering_suggestions);
  addListSection(lines, "### Remote Fit Suggestions", improvement?.remote_fit_suggestions);

  addBulletSection(lines, "## Decision Tracking", [
    ["Status", decision?.decision_status ?? decision?.status ?? item.decision_status],
    ["Priority", decision?.priority],
    ["Notes", decision?.notes],
    ["Next Action", decision?.next_action],
  ]);

  addBulletSection(lines, "## Company Watch", [
    ["Watched", watchlist || item.company_watch_status ? "Yes" : "No"],
    ["Priority", watchlist?.priority],
    ["Reason", watchlist?.interest_reason],
    ["Tags", normalizeTextList(watchlist?.tags).join(", ")],
  ]);

  addBulletSection(lines, "## Links", [
    ["Job", jobUrl],
    ["Apply", applyUrl],
    ["Workspace", workspaceUrl],
    ["Pipeline", "/jobs/pipeline"],
    ["Company Watchlist", "/companies/watchlist"],
  ]);

  return lines.join("\n").replace(/\n{3,}/g, "\n\n").trimEnd() + "\n";
}

export function buildApplicationExportFilename(reviewItem: DailyScoutReviewItem, generatedAt = new Date()) {
  const date = generatedAt.toISOString().slice(0, 10);
  const company = slugify(reviewItem.company_name ?? "");
  const title = slugify(reviewItem.title ?? "");
  const fallback = slugify(reviewItem.job_id ?? "job");
  const parts = ["scoutai", "application", "pack", company, title].filter(Boolean);
  const base = parts.length > 3 ? parts.join("-") : `scoutai-application-pack-${fallback}`;
  return `${base.slice(0, 120).replace(/-+$/g, "")}-${date}.md`;
}

export async function copyApplicationPackMarkdown(markdown: string) {
  try {
    if (!navigator?.clipboard?.writeText) {
      return { ok: false, error: "Clipboard is unavailable in this browser." };
    }
    await navigator.clipboard.writeText(markdown);
    return { ok: true };
  } catch {
    return { ok: false, error: "Could not copy Markdown." };
  }
}

export function downloadMarkdownFile(filename: string, markdown: string) {
  try {
    if (typeof Blob === "undefined" || typeof URL === "undefined" || !URL.createObjectURL) {
      return { ok: false, error: "Downloads are unavailable in this browser." };
    }
    const blob = new Blob([markdown], { type: "text/markdown;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = filename;
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
    URL.revokeObjectURL(url);
    return { ok: true };
  } catch {
    return { ok: false, error: "Could not download Markdown." };
  }
}

export function normalizeTextList(value: unknown): string[] {
  if (!value) return [];
  if (Array.isArray(value)) {
    return value.map(itemToText).filter(Boolean);
  }
  const text = itemToText(value);
  return text ? [text] : [];
}

export function normalizeChecklist(value: unknown) {
  return normalizeTextList(value);
}

export function normalizeRiskList(value: unknown) {
  return normalizeTextList(value);
}

export function normalizeLink(value: unknown) {
  if (typeof value !== "string") return null;
  return normalizeExternalUrl(value) ?? cleanInline(value) ?? null;
}

export function renderMarkdownList(items: unknown) {
  return normalizeTextList(items).map((item) => `- ${item}`).join("\n");
}

export function renderMarkdownChecklist(items: unknown) {
  return normalizeChecklist(items).map((item) => `- [ ] ${item}`).join("\n");
}

function addBulletSection(lines: string[], title: string, fields: Array<[string, MarkdownValue]>) {
  const values = fields
    .map(([label, value]) => [label, cleanInline(value)] as const)
    .filter(([, value]) => value);
  if (!values.length) return;
  lines.push(title);
  lines.push(...values.map(([label, value]) => `- ${label}: ${value}`));
  lines.push("");
}

function addParagraphSection(lines: string[], title: string, value: MarkdownValue) {
  const cleaned = cleanBlock(value);
  if (!cleaned) return;
  lines.push(title);
  lines.push("");
  lines.push(cleaned);
  lines.push("");
}

function addListSection(lines: string[], title: string, items: unknown) {
  const values = normalizeTextList(items);
  if (!values.length) return;
  lines.push(title);
  lines.push(...values.map((item) => `- ${item}`));
  lines.push("");
}

function addChecklistSection(lines: string[], title: string, items: unknown) {
  const values = normalizeChecklist(items);
  if (!values.length) return;
  lines.push(title);
  lines.push(...values.map((item) => `- [ ] ${item}`));
  lines.push("");
}

function addColdDmDrafts(lines: string[], drafts?: Array<ColdDmDraftResult | SavedColdDmDraft> | null) {
  const valid = (drafts ?? []).filter((draft) => cleanBlock(draft.body));
  if (!valid.length) return;
  lines.push("## Cold DM Drafts");
  for (const draft of valid) {
    const title = cleanInline(draft.title) || `${cleanInline(draft.targetType)} draft`;
    lines.push(`### ${title}`);
    if (cleanInline(draft.subjectLine)) lines.push(`Subject: ${cleanInline(draft.subjectLine)}`);
    lines.push("");
    lines.push(cleanBlock(draft.body));
    lines.push("");
  }
}

function addSubList(lines: string[], title: string, items: unknown) {
  const values = normalizeTextList(items);
  if (!values.length) return;
  lines.push(title);
  lines.push(...values.map((item) => `- ${item}`));
}

function addSubParagraph(lines: string[], title: string, value: MarkdownValue) {
  const cleaned = cleanBlock(value);
  if (!cleaned) return;
  lines.push(title);
  lines.push("");
  lines.push(cleaned);
}

function reviewItemResumeFit(item: DailyScoutReviewItem): ResumeFitResult | null {
  if (!item.resume_analysis_status) return null;
  return {
    resume_fit_score: item.resume_fit_score ?? null,
    resume_fit_tier: item.resume_fit_tier ?? "unknown",
    resume_fit_summary: item.resume_fit_summary ?? null,
    resume_strengths: item.resume_strengths ?? [],
    resume_gaps: item.resume_gaps ?? [],
    resume_bullet_sources: item.resume_bullet_sources ?? [],
    resume_action: item.resume_action ?? "needs_review",
    resume_analysis_status: item.resume_analysis_status,
    resume_analysis_error: item.resume_analysis_error,
  };
}

function prepHasContent(prep?: ApplicationPrepResponse | null) {
  return Boolean(
    prep?.fit_summary ||
      prep?.suggested_next_action ||
      prep?.cold_dm_angle ||
      normalizeTextList(prep?.project_talking_points).length ||
      normalizeTextList(prep?.concerns).length ||
      normalizeTextList(prep?.missing_information).length,
  );
}

function itemToText(item: unknown): string {
  if (typeof item === "string" || typeof item === "number" || typeof item === "boolean") {
    return cleanInline(item);
  }
  if (!item || typeof item !== "object") return "";
  const record = item as Record<string, unknown>;
  const primary =
    pick(record, "bullet_template") ??
    pick(record, "suggestion") ??
    pick(record, "action") ??
    pick(record, "value") ??
    pick(record, "label") ??
    pick(record, "title") ??
    "";
  const label = pick(record, "section") ?? pick(record, "category") ?? pick(record, "skill") ?? pick(record, "target_section") ?? "";
  const reason = pick(record, "reason");
  const priority = pick(record, "priority");
  const severity = pick(record, "severity");
  const evidence = pick(record, "supporting_evidence") ?? pick(record, "evidence");
  const caution = pick(record, "caution");
  const requirement = pick(record, "required_or_preferred");
  const children = normalizeTextList(record.items);
  const parts = [
    label ? `${cleanInline(label)}: ${cleanInline(primary)}` : cleanInline(primary),
    requirement ? `Requirement: ${cleanInline(requirement)}` : "",
    reason ? `Reason: ${cleanInline(reason)}` : "",
    priority ? `Priority: ${cleanInline(priority)}` : "",
    severity ? `Severity: ${cleanInline(severity)}` : "",
    evidence ? `Evidence: ${cleanInline(evidence)}` : "",
    caution ? `Caution: ${cleanInline(caution)}` : "",
    children.length ? children.join("; ") : "",
  ].filter(Boolean);
  return parts.join(" - ");
}

function pick(record: Record<string, unknown>, key: string) {
  if (blockedKeys.has(key)) return null;
  const value = record[key];
  if (typeof value === "string" || typeof value === "number" || typeof value === "boolean") {
    return String(value);
  }
  return null;
}

function activeResumeLabel(resume?: ResumeResponse | null) {
  if (!resume) return null;
  const filename = cleanInline(resume.original_filename ?? resume.filename ?? "Active resume");
  return `${filename}${resume.parse_status ? ` (${cleanInline(resume.parse_status)})` : ""}`;
}

function scoreLabel(value: unknown) {
  if (typeof value === "number" && Number.isFinite(value)) return String(Math.round(value));
  if (typeof value === "string" && value.trim()) return cleanInline(value);
  return null;
}

function cleanInline(value: MarkdownValue) {
  if (value == null) return "";
  return String(value)
    .replace(/\r\n/g, "\n")
    .replace(/\s+/g, " ")
    .replace(/[<>]/g, "")
    .replace(/[|`]/g, "")
    .trim();
}

function cleanBlock(value: MarkdownValue) {
  if (value == null) return "";
  return String(value)
    .replace(/\r\n/g, "\n")
    .replace(/[<>]/g, "")
    .replace(/[|`]/g, "")
    .replace(/[ \t]+\n/g, "\n")
    .replace(/\n[ \t]+/g, "\n")
    .replace(/\n{3,}/g, "\n\n")
    .trim();
}

function slugify(value: string) {
  return value
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
}
