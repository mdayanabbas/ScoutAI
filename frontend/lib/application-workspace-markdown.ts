import type { ApplicationPacketResponse } from "@/types/application-packet";
import type { ApplicationPrepResponse } from "@/types/application-prep";
import type { JobApplicationDecisionResponse, JobDecisionStatus } from "@/types/job-decision";
import type { ResumeImprovementResponse } from "@/types/resume-improvement";
import type { ResumeResponse } from "@/types/resume";

type MarkdownValue = string | number | boolean | null | undefined;

export type WorkspaceMarkdownChecklistItem = {
  label: string;
  checked?: boolean;
};

export type WorkspaceMarkdownJobSummary = {
  title?: string | null;
  companyName?: string | null;
  role?: string | null;
  source?: string | null;
  applyUrl?: string | null;
  matchTier?: string | null;
  totalScore?: number | null;
  remoteEligibility?: string | null;
  decisionStatus?: JobDecisionStatus | null;
};

export type ApplicationWorkspaceMarkdownInput = {
  job: WorkspaceMarkdownJobSummary;
  activeResume?: ResumeResponse | null;
  packet?: ApplicationPacketResponse | null;
  improvement?: ResumeImprovementResponse | null;
  prep?: ApplicationPrepResponse | null;
  checklist?: WorkspaceMarkdownChecklistItem[];
  notes?: string | null;
  exportedAt?: Date;
};

const blockedKeys = new Set(["raw_text", "rawText", "storage_path", "storagePath"]);

export function buildApplicationWorkspaceMarkdown(input: ApplicationWorkspaceMarkdownInput) {
  const job = input.job;
  const packet = input.packet ?? null;
  const improvement = input.improvement ?? null;
  const prep = input.prep ?? null;
  const exportedAt = input.exportedAt ?? new Date();
  const title = cleanInline(job.title) || "Job";
  const company = cleanInline(job.companyName) || "Unknown Company";
  const lines: string[] = [];

  lines.push(`# Application Workspace - ${title} at ${company}`);
  lines.push("");
  lines.push("## Job Summary");
  lines.push(...bulletFields([
    ["Company", company],
    ["Role", job.role ?? title],
    ["Match Tier", job.matchTier],
    ["Score", job.totalScore == null ? null : String(Math.round(job.totalScore))],
    ["Remote Eligibility", job.remoteEligibility],
    ["Source", job.source],
    ["Apply URL", job.applyUrl],
    ["Decision Status", job.decisionStatus],
  ]));
  lines.push("");

  lines.push("## Resume Status");
  lines.push(...bulletFields([
    ["Active Resume", activeResumeLabel(input.activeResume)],
    ["Resume Used", yesNo(packet?.resume_used ?? improvement?.resume_used)],
    ["Resume Match Summary", packet?.resume_match_summary],
  ]));
  lines.push("");

  lines.push("## Application Positioning");
  lines.push(paragraph(packet?.application_positioning));
  lines.push("");

  addListSection(lines, "## Resume Strengths", packet?.resume_strengths);
  addListSection(lines, "## Resume Gaps", packet?.resume_gaps);

  lines.push("## Resume Improvement Suggestions");
  addSubListSection(lines, "### Section Suggestions", improvement?.section_suggestions);
  addSubListSection(lines, "### Resume Bullet Suggestions", improvement?.bullet_suggestions);
  addSubListSection(lines, "### Skill Gaps", improvement?.skill_gap_suggestions);
  addSubListSection(lines, "### Project Reordering", improvement?.project_reordering_suggestions);
  addSubListSection(lines, "### Remote Fit Suggestions", improvement?.remote_fit_suggestions);

  lines.push("## Application Packet");
  addSubListSection(lines, "### Resume Focus", packet?.resume_focus);
  addSubListSection(lines, "### Resume Bullet Suggestions", packet?.resume_bullet_suggestions);
  addSubListSection(lines, "### Project Evidence", packet?.project_evidence_to_use);
  addSubListSection(lines, "### Cover Note Outline", packet?.cover_note_outline?.items);
  addSubListSection(lines, "### Cold DM Outline", packet?.cold_dm_outline?.items);
  addSubListSection(lines, "### Risks To Verify", packet?.risks_to_verify);
  addSubListSection(lines, "### Suggested Apply Plan", packet?.suggested_apply_plan, true);

  lines.push("## Application Prep Notes");
  lines.push(...bulletFields([
    ["Fit Summary", prep?.fit_summary],
    ["Concerns", listInline(prep?.concerns)],
    ["Missing Information", listInline(prep?.missing_information)],
    ["Next Action", prep?.suggested_next_action],
  ]));
  lines.push("");

  lines.push("## Checklist");
  if (input.checklist?.length) {
    lines.push(...input.checklist.map((item) => `- [${item.checked ? "x" : " "}] ${cleanInline(item.label)}`));
  } else {
    lines.push("Not generated yet.");
  }
  lines.push("");

  lines.push("## Personal Notes");
  lines.push(paragraph(input.notes));
  lines.push("");

  lines.push("## Export Metadata");
  lines.push("- Generated from ScoutAI");
  lines.push(`- Exported at: ${exportedAt.toISOString()}`);
  lines.push("");

  return lines.join("\n").replace(/\n{3,}/g, "\n\n").trimEnd() + "\n";
}

export function buildWorkspaceMarkdownFilename(company?: string | null, role?: string | null) {
  const companySlug = slugify(company || "unknown-company");
  const roleSlug = slugify(role || "job");
  const base = `scoutai-${companySlug}-${roleSlug}-workspace`;
  return `${base.slice(0, 110).replace(/-+$/g, "")}.md`;
}

function addListSection(lines: string[], title: string, items: unknown) {
  lines.push(title);
  const formatted = formatList(items);
  lines.push(...(formatted.length ? formatted : ["Not generated yet."]));
  lines.push("");
}

function addSubListSection(lines: string[], title: string, items: unknown, ordered = false) {
  lines.push(title);
  const formatted = formatList(items, ordered);
  lines.push(...(formatted.length ? formatted : ["Not generated yet."]));
  lines.push("");
}

function bulletFields(fields: Array<[string, MarkdownValue]>) {
  return fields.map(([label, value]) => `- ${label}: ${cleanInline(value) || "Not generated yet."}`);
}

function formatList(items: unknown, ordered = false) {
  const values = normalizeItems(items);
  return values.map((value, index) => `${ordered ? `${index + 1}.` : "-"} ${value}`);
}

function listInline(items: unknown) {
  const values = normalizeItems(items);
  return values.length ? values.join("; ") : null;
}

function normalizeItems(items: unknown): string[] {
  if (!items) {
    return [];
  }
  if (!Array.isArray(items)) {
    const value = itemToText(items);
    return value ? [value] : [];
  }
  return items.map(itemToText).filter(Boolean);
}

function itemToText(item: unknown): string {
  if (typeof item === "string" || typeof item === "number" || typeof item === "boolean") {
    return cleanInline(item);
  }
  if (!item || typeof item !== "object") {
    return "";
  }

  const record = item as Record<string, unknown>;
  const primary =
    pick(record, "bullet_template") ??
    pick(record, "suggestion") ??
    pick(record, "value") ??
    pick(record, "label") ??
    pick(record, "title") ??
    "";
  const label = pick(record, "section") ?? pick(record, "category") ?? pick(record, "skill") ?? "";
  const reason = pick(record, "reason");
  const priority = pick(record, "priority");
  const caution = pick(record, "caution");
  const evidence = pick(record, "supporting_evidence") ?? pick(record, "evidence");
  const children = normalizeItems(record.items);
  const parts = [
    label ? `${cleanInline(label)}: ${cleanInline(primary)}` : cleanInline(primary),
    reason ? `Reason: ${cleanInline(reason)}` : "",
    priority ? `Priority: ${cleanInline(priority)}` : "",
    evidence ? `Evidence: ${cleanInline(evidence)}` : "",
    caution ? `Caution: ${cleanInline(caution)}` : "",
    children.length ? children.join("; ") : "",
  ].filter(Boolean);
  return parts.join(" - ");
}

function pick(record: Record<string, unknown>, key: string) {
  if (blockedKeys.has(key)) {
    return null;
  }
  const value = record[key];
  if (typeof value === "string" || typeof value === "number" || typeof value === "boolean") {
    return String(value);
  }
  return null;
}

function paragraph(value: MarkdownValue) {
  return cleanBlock(value) || "Not generated yet.";
}

function activeResumeLabel(resume?: ResumeResponse | null) {
  if (!resume) {
    return "No active resume";
  }
  const filename = cleanInline(resume.original_filename ?? resume.filename ?? "Active resume");
  return `${filename}${resume.parse_status ? ` (${cleanInline(resume.parse_status)})` : ""}`;
}

function yesNo(value?: boolean | null) {
  if (value == null) {
    return null;
  }
  return value ? "Yes" : "No";
}

function cleanInline(value: MarkdownValue) {
  if (value == null) {
    return "";
  }
  return String(value)
    .replace(/\r\n/g, "\n")
    .replace(/\s+/g, " ")
    .replace(/[<>]/g, "")
    .replace(/[|`]/g, "")
    .trim();
}

function cleanBlock(value: MarkdownValue) {
  if (value == null) {
    return "";
  }
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
  const slug = value
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
  return slug || "workspace";
}
