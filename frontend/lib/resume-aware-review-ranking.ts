import type { ApplicationPacketResponse } from "@/types/application-packet";
import type { ResumeImprovementResponse } from "@/types/resume-improvement";
import type {
  DailyScoutReviewItem,
  ResumeAction,
  ResumeAnalysisStatus,
  ResumeFitTier,
} from "@/lib/daily-scout-review-queue";

export type ResumeFitResult = {
  resume_fit_score: number | null;
  resume_fit_tier: ResumeFitTier;
  resume_fit_summary: string | null;
  resume_strengths: string[];
  resume_gaps: string[];
  resume_bullet_sources: string[];
  resume_action: ResumeAction;
  resume_analysis_status: ResumeAnalysisStatus;
  resume_analysis_error?: string | null;
};

export type ResumeFitCacheEntry = ResumeFitResult & {
  job_id: string;
  resume_id: string;
  updated_at: string;
};

export const resumeFitCacheKey = "scoutai.dailyScout.resumeFit.v1";

export function deriveResumeFitFromPacket(
  packet?: ApplicationPacketResponse | null,
  improvement?: ResumeImprovementResponse | null,
  item?: DailyScoutReviewItem,
): ResumeFitResult {
  const resumeUsed = Boolean(packet?.resume_used || improvement?.resume_used);
  const strengths = normalizeEvidence(packet?.resume_strengths);
  const gaps = [
    ...normalizeEvidence(packet?.resume_gaps),
    ...normalizeEvidence(improvement?.skill_gap_suggestions).filter((value) => /missing|required|gap|not found/i.test(value)),
  ];
  const bulletSources = normalizeEvidence(packet?.resume_bullet_sources);
  const risks = [
    ...normalizeEvidence(packet?.risks_to_verify),
    ...normalizeEvidence(improvement?.risks),
    ...normalizeEvidence(improvement?.remote_fit_suggestions).filter((value) => /risk|verify|unclear|restricted/i.test(value)),
  ];
  const summary = packet?.resume_match_summary ?? improvement?.improvement_summary ?? null;

  if (!resumeUsed && !strengths.length && !gaps.length && !bulletSources.length && !summary) {
    return {
      resume_fit_score: null,
      resume_fit_tier: "unknown",
      resume_fit_summary: null,
      resume_strengths: [],
      resume_gaps: [],
      resume_bullet_sources: [],
      resume_action: "needs_review",
      resume_analysis_status: "unavailable",
    };
  }

  let score = numberValue(packet?.total_score) ?? numberValue(improvement?.total_score) ?? numberValue(item?.total_score) ?? 50;
  if (strengths.length >= 3) score += 10;
  if (bulletSources.length > 0) score += 8;
  if (summary && /strong|good|fit|matches|aligned|relevant/i.test(summary)) score += 5;
  if (roleAlignsWithEvidence(item, strengths, bulletSources)) score += 5;
  if (gaps.some(isMajorGap)) score -= 10;
  if (risks.some(isMajorRisk)) score -= 10;
  if (/tailor|rewrite|add|missing|heavy/i.test(improvement?.suggested_next_action ?? "")) score -= 8;
  if (item?.eligibility_status === "uncertain") score -= 8;
  if (item?.match_tier === "stretch" && gaps.length >= 3) score -= 12;

  const clamped = clamp(score);
  const tier = tierFromScore(clamped);
  return {
    resume_fit_score: clamped,
    resume_fit_tier: tier,
    resume_fit_summary: summary,
    resume_strengths: strengths,
    resume_gaps: gaps,
    resume_bullet_sources: bulletSources,
    resume_action: actionFromFit(tier, item, gaps, risks),
    resume_analysis_status: "ready",
  };
}

export function buildResumeAwareReviewRanking(items: DailyScoutReviewItem[]) {
  const rankedItems = [...items].sort((a, b) => resumeRank(a) - resumeRank(b) || genericRank(a) - genericRank(b));
  const summary = {
    analyzed: items.filter((item) => item.resume_analysis_status === "ready").length,
    strong_fit: items.filter((item) => item.resume_fit_tier === "strong_fit").length,
    good_fit: items.filter((item) => item.resume_fit_tier === "good_fit").length,
    needs_tailoring: items.filter((item) => item.resume_fit_tier === "needs_tailoring").length,
    weak_fit: items.filter((item) => item.resume_fit_tier === "weak_fit").length,
    unknown: items.filter((item) => !item.resume_fit_tier || item.resume_fit_tier === "unknown").length,
    apply_now: items.filter((item) => item.resume_action === "apply_now").length,
    tailor_resume: items.filter((item) => item.resume_action === "tailor_resume").length,
    cold_dm_first: items.filter((item) => item.resume_action === "cold_dm_first").length,
  };
  return { rankedItems, summary };
}

export function getResumeFitCache(): ResumeFitCacheEntry[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = window.localStorage.getItem(resumeFitCacheKey);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed.filter(isCacheEntry) : [];
  } catch {
    return [];
  }
}

export function saveResumeFitCache(entries: ResumeFitCacheEntry[]) {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(resumeFitCacheKey, JSON.stringify(entries.map(lightweightEntry)));
  } catch {
    // Derived resume fit cache is optional.
  }
}

export function upsertResumeFitCache(
  entries: ResumeFitCacheEntry[],
  jobId: string,
  resumeId: string,
  result: ResumeFitResult,
) {
  const next = entries.filter((entry) => !(entry.job_id === jobId && entry.resume_id === resumeId));
  next.push(lightweightEntry({ ...result, job_id: jobId, resume_id: resumeId, updated_at: new Date().toISOString() }));
  saveResumeFitCache(next);
  return next;
}

export function cacheEntryToReviewFields(entry: ResumeFitCacheEntry): ResumeFitResult {
  return {
    resume_fit_score: entry.resume_fit_score,
    resume_fit_tier: entry.resume_fit_tier,
    resume_fit_summary: entry.resume_fit_summary,
    resume_strengths: entry.resume_strengths ?? [],
    resume_gaps: entry.resume_gaps ?? [],
    resume_bullet_sources: entry.resume_bullet_sources ?? [],
    resume_action: entry.resume_action,
    resume_analysis_status: entry.resume_analysis_status,
  };
}

function resumeRank(item: DailyScoutReviewItem) {
  const tier = item.resume_fit_tier ?? "unknown";
  const action = item.resume_action;
  if (tier === "strong_fit") return action === "apply_now" ? 0 : 1;
  if (tier === "good_fit") return 2;
  if (tier === "needs_tailoring") return 3;
  if (tier === "unknown") return 4;
  return 8;
}

function genericRank(item: DailyScoutReviewItem) {
  return (
    tierRank(item.match_tier) * 1000 +
    eligibilityRank(item.eligibility_status) * 100 +
    (100 - (item.total_score ?? 0))
  );
}

function tierRank(value?: string | null) {
  const tier = String(value ?? "").toLowerCase();
  if (tier === "best_match" || tier === "best") return 0;
  if (tier === "strong_match") return 1;
  if (tier === "worth_checking") return 2;
  if (tier === "stretch") return 4;
  return 3;
}

function eligibilityRank(value?: string | null) {
  const status = String(value ?? "").toLowerCase();
  if (status === "eligible") return 0;
  if (status === "stretch") return 2;
  if (status === "uncertain") return 3;
  return 4;
}

function tierFromScore(score: number): ResumeFitTier {
  if (score >= 80) return "strong_fit";
  if (score >= 65) return "good_fit";
  if (score >= 45) return "needs_tailoring";
  return "weak_fit";
}

function actionFromFit(
  tier: ResumeFitTier,
  item: DailyScoutReviewItem | undefined,
  gaps: string[],
  risks: string[],
): ResumeAction {
  if (String(item?.eligibility_status ?? "").toLowerCase() === "unsuitable" || risks.some(isMajorRisk)) return "skip_for_now";
  if (tier === "strong_fit" && ["eligible", "best_match", "strong_match"].includes(String(item?.eligibility_status ?? item?.match_tier ?? ""))) return "apply_now";
  if (tier === "strong_fit" && gaps.length > 0) return "create_project_angle";
  if (tier === "good_fit" || tier === "needs_tailoring") return "tailor_resume";
  if (tier === "weak_fit" && item?.company_name) return "cold_dm_first";
  return "needs_review";
}

function roleAlignsWithEvidence(item: DailyScoutReviewItem | undefined, strengths: string[], bullets: string[]) {
  const titleWords = String(item?.title ?? "")
    .toLowerCase()
    .split(/[^a-z0-9]+/)
    .filter((word) => word.length > 3);
  const evidence = [...strengths, ...bullets].join(" ").toLowerCase();
  return titleWords.some((word) => evidence.includes(word));
}

function normalizeEvidence(values: unknown) {
  if (!Array.isArray(values)) return [];
  return values.map(stringFromUnknown).filter(Boolean).slice(0, 8);
}

function stringFromUnknown(value: unknown): string {
  if (typeof value === "string") return value.trim();
  if (!value || typeof value !== "object") return "";
  const object = value as Record<string, unknown>;
  return String(object.value ?? object.suggestion ?? object.reason ?? object.label ?? object.skill ?? object.bullet_template ?? "")
    .trim();
}

function isMajorGap(value: string) {
  return /missing|required|must|gap|not found|unsupported/i.test(value);
}

function isMajorRisk(value: string) {
  return /authorization|visa|remote|onsite|senior|principal|staff|risk|restricted|not eligible/i.test(value);
}

function numberValue(value: unknown) {
  if (typeof value === "number" && Number.isFinite(value)) return value;
  if (typeof value === "string" && value.trim()) {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : null;
  }
  return null;
}

function clamp(value: number) {
  return Math.max(0, Math.min(100, Math.round(value)));
}

function lightweightEntry(entry: ResumeFitCacheEntry): ResumeFitCacheEntry {
  return {
    job_id: entry.job_id,
    resume_id: entry.resume_id,
    resume_fit_score: entry.resume_fit_score,
    resume_fit_tier: entry.resume_fit_tier,
    resume_fit_summary: entry.resume_fit_summary,
    resume_strengths: (entry.resume_strengths ?? []).slice(0, 4),
    resume_gaps: (entry.resume_gaps ?? []).slice(0, 4),
    resume_bullet_sources: (entry.resume_bullet_sources ?? []).slice(0, 4),
    resume_action: entry.resume_action,
    resume_analysis_status: entry.resume_analysis_status,
    updated_at: entry.updated_at,
  };
}

function isCacheEntry(value: unknown): value is ResumeFitCacheEntry {
  if (!value || typeof value !== "object") return false;
  const entry = value as ResumeFitCacheEntry;
  return typeof entry.job_id === "string" && typeof entry.resume_id === "string";
}
