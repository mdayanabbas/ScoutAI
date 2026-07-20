import type { DailyScoutReviewItem } from "@/lib/daily-scout-review-queue";
import type { ResumeFitResult } from "@/lib/resume-aware-review-ranking";
import type { ApplicationPacketResponse } from "@/types/application-packet";
import type { ApplicationPrepResponse } from "@/types/application-prep";
import type { CompanyWatchlistResponse } from "@/types/company-watchlist";
import type { JobApplicationDecisionResponse } from "@/types/job-decision";
import type { ResumeResponse } from "@/types/resume";
import type { ResumeImprovementResponse } from "@/types/resume-improvement";

export type ColdDmTargetType =
  | "founder"
  | "recruiter"
  | "hiring_manager"
  | "team_member"
  | "twitter_dm"
  | "linkedin_connection"
  | "follow_up";

export type ColdDmTone = "direct" | "warm" | "confident" | "concise" | "technical" | "humble";
export type ColdDmLength = "short" | "medium" | "detailed";

export type ColdDmDraftInput = {
  reviewItem: DailyScoutReviewItem;
  activeResume?: ResumeResponse | null;
  resumeFitResult?: ResumeFitResult | null;
  applicationPacket?: ApplicationPacketResponse | null;
  resumeImprovement?: ResumeImprovementResponse | null;
  prepNotes?: ApplicationPrepResponse | null;
  decision?: JobApplicationDecisionResponse | null;
  watchlistItem?: CompanyWatchlistResponse | null;
  targetType: ColdDmTargetType;
  tone: ColdDmTone;
  length: ColdDmLength;
  includeProjects: boolean;
  includeResumeFit: boolean;
  includeRemoteFit: boolean;
  includeAsk: boolean;
  includeColdDmOutline?: boolean;
  customRecipientName?: string;
  customCompanyContext?: string;
  customProofPoint?: string;
  customAsk?: string;
};

export type ColdDmDraftResult = {
  id: string;
  targetType: ColdDmTargetType;
  tone: ColdDmTone;
  length: ColdDmLength;
  title: string;
  body: string;
  subjectLine: string;
  characterCount: number;
  wordCount: number;
  warnings: string[];
  generatedAt: string;
  sourceJobId: string;
};

export type SavedColdDmDraft = Pick<
  ColdDmDraftResult,
  "id" | "targetType" | "tone" | "length" | "body" | "generatedAt" | "sourceJobId"
> & {
  job_id: string;
  company_name?: string | null;
  job_title?: string | null;
  title?: string;
  subjectLine?: string;
};

export const coldDmDraftStorageKey = "scoutai.coldDmDrafts.v1";

export const coldDmTargetOptions: Array<{ value: ColdDmTargetType; label: string }> = [
  { value: "founder", label: "Founder" },
  { value: "recruiter", label: "Recruiter" },
  { value: "hiring_manager", label: "Hiring Manager" },
  { value: "team_member", label: "Team Member" },
  { value: "twitter_dm", label: "X/Twitter DM" },
  { value: "linkedin_connection", label: "LinkedIn Connection Note" },
  { value: "follow_up", label: "Follow-up" },
];

export const coldDmToneOptions: Array<{ value: ColdDmTone; label: string }> = [
  { value: "direct", label: "Direct" },
  { value: "warm", label: "Warm" },
  { value: "confident", label: "Confident" },
  { value: "concise", label: "Concise" },
  { value: "technical", label: "Technical" },
  { value: "humble", label: "Humble" },
];

export const coldDmLengthOptions: Array<{ value: ColdDmLength; label: string }> = [
  { value: "short", label: "Short" },
  { value: "medium", label: "Medium" },
  { value: "detailed", label: "Detailed" },
];

export function defaultColdDmLength(targetType: ColdDmTargetType): ColdDmLength {
  if (targetType === "twitter_dm" || targetType === "linkedin_connection" || targetType === "follow_up") return "short";
  return "medium";
}

export function buildColdDmDraft(input: ColdDmDraftInput): ColdDmDraftResult {
  const jobTitle = clean(input.reviewItem.title) || clean(input.applicationPacket?.title) || clean(input.prepNotes?.title) || "the role";
  const company = clean(input.reviewItem.company_name) || clean(input.applicationPacket?.company_name) || clean(input.prepNotes?.company_name) || "the company";
  const recipient = clean(input.customRecipientName) || "there";
  const context = clean(input.customCompanyContext);
  const proof = proofPoint(input);
  const fit = input.includeResumeFit ? resumeFitLine(input) : "";
  const project = input.includeProjects ? projectEvidence(input) : "";
  const remote = input.includeRemoteFit ? remoteFitLine(input.reviewItem.remote_eligibility) : "";
  const ask = input.includeAsk ? clean(input.customAsk) || defaultAsk(input.targetType) : "";
  const outline = input.includeColdDmOutline ? firstText(input.applicationPacket?.cold_dm_outline?.items) || clean(input.prepNotes?.cold_dm_angle) : "";
  const warnings = buildWarnings(input, company, jobTitle, proof, ask);
  const body = tighten(templateBody({
    targetType: input.targetType,
    tone: input.tone,
    length: input.length,
    recipient,
    company,
    jobTitle,
    context,
    proof,
    fit,
    project,
    remote,
    ask,
    outline,
  }));
  const limitedBody = limitBody(body, input.targetType, input.length);
  if (input.targetType === "twitter_dm" && limitedBody.length > 280) warnings.push("Message is longer than a typical X/Twitter DM.");
  if (input.targetType === "linkedin_connection" && limitedBody.length > 300) warnings.push("Message is longer than a typical LinkedIn connection note.");

  return {
    id: `cold-dm-${input.reviewItem.job_id || "job"}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
    targetType: input.targetType,
    tone: input.tone,
    length: input.length,
    title: `${targetLabel(input.targetType)} draft for ${company}`,
    subjectLine: subjectLine(input.targetType, company, jobTitle),
    body: limitedBody,
    characterCount: limitedBody.length,
    wordCount: wordCount(limitedBody),
    warnings,
    generatedAt: new Date().toISOString(),
    sourceJobId: input.reviewItem.job_id,
  };
}

export function generateColdDmVariants(input: Omit<ColdDmDraftInput, "tone">) {
  return (["direct", "warm", "technical"] as ColdDmTone[]).map((tone) => buildColdDmDraft({ ...input, tone }));
}

export async function copyColdDmDraft(body: string) {
  try {
    if (!navigator?.clipboard?.writeText) return { ok: false, error: "Clipboard is unavailable in this browser." };
    await navigator.clipboard.writeText(body);
    return { ok: true };
  } catch {
    return { ok: false, error: "Could not copy draft." };
  }
}

export function getSavedColdDmDrafts(): SavedColdDmDraft[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = window.localStorage.getItem(coldDmDraftStorageKey);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed.filter(isSavedDraft) : [];
  } catch {
    return [];
  }
}

export function saveColdDmDraft(draft: ColdDmDraftResult, reviewItem: DailyScoutReviewItem) {
  const saved: SavedColdDmDraft = {
    id: draft.id,
    job_id: reviewItem.job_id,
    sourceJobId: draft.sourceJobId,
    company_name: reviewItem.company_name,
    job_title: reviewItem.title,
    targetType: draft.targetType,
    tone: draft.tone,
    length: draft.length,
    title: draft.title,
    subjectLine: draft.subjectLine,
    body: draft.body,
    generatedAt: draft.generatedAt,
  };
  const next = [saved, ...getSavedColdDmDrafts().filter((item) => item.id !== draft.id)].slice(0, 100);
  try {
    window.localStorage.setItem(coldDmDraftStorageKey, JSON.stringify(next));
  } catch {
    return { ok: false, error: "Could not save draft locally." };
  }
  return { ok: true, draft: saved };
}

export function deleteSavedColdDmDraft(draftId: string) {
  const next = getSavedColdDmDrafts().filter((item) => item.id !== draftId);
  try {
    window.localStorage.setItem(coldDmDraftStorageKey, JSON.stringify(next));
    return { ok: true };
  } catch {
    return { ok: false, error: "Could not delete saved draft." };
  }
}

export function savedDraftsForJob(jobId: string) {
  return getSavedColdDmDrafts().filter((draft) => draft.job_id === jobId || draft.sourceJobId === jobId);
}

function templateBody(input: {
  targetType: ColdDmTargetType;
  tone: ColdDmTone;
  length: ColdDmLength;
  recipient: string;
  company: string;
  jobTitle: string;
  context: string;
  proof: string;
  fit: string;
  project: string;
  remote: string;
  ask: string;
  outline: string;
}) {
  const opener = greeting(input.recipient, input.tone);
  const context = input.context ? ` ${input.context}` : "";
  const proof = input.proof ? ` My strongest proof point is ${input.proof}.` : "";
  const fit = input.fit ? ` ${input.fit}` : "";
  const project = input.project ? ` I can point to ${input.project}.` : "";
  const remote = input.remote ? ` ${input.remote}` : "";
  const outline = input.outline ? ` One useful angle: ${input.outline}.` : "";
  const ask = input.ask ? ` ${input.ask}` : "";

  if (input.targetType === "twitter_dm") {
    return `${opener} I saw ${input.company}'s ${input.jobTitle} role and it looks close to my AI/backend work.${proof}${ask}`;
  }
  if (input.targetType === "linkedin_connection") {
    return `${opener} I came across ${input.company}'s ${input.jobTitle} role and would love to connect.${proof || fit}${ask}`;
  }
  if (input.targetType === "follow_up") {
    return `${opener} Quick follow-up on my note about the ${input.jobTitle} role at ${input.company}.${fit || proof}${ask || " Would it be worth a quick look?"}`;
  }
  if (input.targetType === "recruiter") {
    return `${opener} I came across the ${input.jobTitle} role at ${input.company} and wanted to share my interest.${fit}${proof}${remote}${ask || " Would you be open to considering my profile for the process?"}`;
  }
  if (input.targetType === "hiring_manager") {
    return `${opener} I saw ${input.company}'s ${input.jobTitle} role and it stood out because it maps to the kind of technical work I want to do.${proof}${project}${fit}${ask || " Would you be open to a short conversation about whether my background fits what the team needs?"}`;
  }
  if (input.targetType === "team_member") {
    return `${opener} I noticed ${input.company} is hiring for ${input.jobTitle}.${context}${fit}${proof}${ask || " If you have a moment, I would appreciate any perspective on what the team is looking for."}`;
  }
  return `${opener} I came across ${input.company}'s ${input.jobTitle} role and it stood out because it lines up with the systems I have been building.${context}${proof}${project}${fit}${remote}${outline}${ask || " Would you be open to a quick look at my profile for this role?"}`;
}

function proofPoint(input: ColdDmDraftInput) {
  return clean(input.customProofPoint) ||
    firstText(input.resumeFitResult?.resume_strengths) ||
    firstText(input.applicationPacket?.resume_strengths) ||
    firstText(input.applicationPacket?.resume_bullet_sources) ||
    firstText(input.prepNotes?.resume_focus_points) ||
    firstText(input.resumeImprovement?.bullet_suggestions) ||
    "";
}

function projectEvidence(input: ColdDmDraftInput) {
  return firstText(input.applicationPacket?.project_evidence_to_use) ||
    firstText(input.prepNotes?.project_talking_points) ||
    firstText(input.resumeImprovement?.project_reordering_suggestions) ||
    "";
}

function resumeFitLine(input: ColdDmDraftInput) {
  const summary = clean(input.resumeFitResult?.resume_fit_summary) || clean(input.applicationPacket?.resume_match_summary);
  if (summary) return summary;
  const tier = input.resumeFitResult?.resume_fit_tier;
  if (tier && tier !== "unknown") return `ScoutAI flags this as a ${tier.replace(/_/g, " ")}.`;
  return "";
}

function remoteFitLine(value?: string | null) {
  if (!value) return "";
  if (/remote|work_from_anywhere/i.test(value)) return "The remote setup also looks aligned with my search.";
  if (/hybrid/i.test(value)) return "I would want to confirm the hybrid expectations, but the role still looks worth a conversation.";
  return "";
}

function defaultAsk(targetType: ColdDmTargetType) {
  if (targetType === "team_member") return "Would you be open to sharing what the team is looking for?";
  if (targetType === "recruiter") return "Would you be open to considering my profile for the process?";
  if (targetType === "twitter_dm") return "Open to a quick look?";
  if (targetType === "linkedin_connection") return "Would be glad to connect.";
  if (targetType === "follow_up") return "Would it be worth a quick look?";
  return "Would you be open to a quick look at my profile for this role?";
}

function buildWarnings(input: ColdDmDraftInput, company: string, jobTitle: string, proof: string, ask: string) {
  const warnings: string[] = [];
  if (!clean(input.reviewItem.company_name) && company === "the company") warnings.push("Company name is missing.");
  if (!clean(input.reviewItem.title) && jobTitle === "the role") warnings.push("Job title is missing.");
  if (!input.resumeFitResult && !input.applicationPacket?.resume_match_summary) warnings.push("No resume fit data is available yet.");
  if (!proof) warnings.push("No clear project or resume proof point is available.");
  if (!ask && input.includeAsk) warnings.push("No clear ask was found.");
  if (!clean(input.customRecipientName) && ["founder", "recruiter", "hiring_manager", "team_member"].includes(input.targetType)) {
    warnings.push("Recipient name is missing, so the draft uses a neutral greeting.");
  }
  return warnings;
}

function limitBody(body: string, targetType: ColdDmTargetType, length: ColdDmLength) {
  const max = targetType === "twitter_dm" ? 320 : targetType === "linkedin_connection" ? 340 : length === "short" ? 520 : length === "medium" ? 900 : 1400;
  if (body.length <= max) return body;
  const sliced = body.slice(0, max).replace(/\s+\S*$/g, "").trim();
  return `${sliced}.`;
}

function firstText(value: unknown): string {
  if (!value) return "";
  if (Array.isArray(value)) {
    for (const item of value) {
      const text = firstText(item);
      if (text) return text;
    }
    return "";
  }
  if (typeof value === "string" || typeof value === "number" || typeof value === "boolean") return clean(value);
  if (typeof value !== "object") return "";
  const record = value as Record<string, unknown>;
  return clean(record.bullet_template) ||
    clean(record.suggestion) ||
    clean(record.value) ||
    clean(record.label) ||
    clean(record.reason) ||
    clean(record.evidence) ||
    clean(record.supporting_evidence) ||
    "";
}

function subjectLine(targetType: ColdDmTargetType, company: string, jobTitle: string) {
  if (targetType === "follow_up") return `Following up on ${jobTitle}`;
  if (targetType === "twitter_dm" || targetType === "linkedin_connection") return "";
  return `${jobTitle} at ${company}`;
}

function greeting(name: string, tone: ColdDmTone) {
  if (tone === "direct" || tone === "concise") return `Hi ${name},`;
  if (tone === "warm" || tone === "humble") return `Hey ${name},`;
  return `Hi ${name},`;
}

function targetLabel(value: ColdDmTargetType) {
  return coldDmTargetOptions.find((item) => item.value === value)?.label ?? value;
}

function wordCount(value: string) {
  return value.trim().split(/\s+/).filter(Boolean).length;
}

function tighten(value: string) {
  return value.replace(/[ \t]+/g, " ").replace(/\s+\./g, ".").replace(/\n{3,}/g, "\n\n").trim();
}

function clean(value: unknown) {
  if (value == null) return "";
  return String(value)
    .replace(/\r\n/g, "\n")
    .replace(/[<>|`]/g, "")
    .replace(/\s+/g, " ")
    .trim();
}

function isSavedDraft(value: unknown): value is SavedColdDmDraft {
  if (!value || typeof value !== "object") return false;
  const record = value as Record<string, unknown>;
  return typeof record.id === "string" && typeof record.body === "string" && typeof record.job_id === "string";
}
