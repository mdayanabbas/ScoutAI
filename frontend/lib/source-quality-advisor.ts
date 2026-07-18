export type SourceRecommendation =
  | "run_daily"
  | "run_every_few_days"
  | "run_weekly"
  | "run_manually"
  | "needs_configuration"
  | "needs_debugging"
  | "not_enough_data";

export type SourceQualityAdvisorInput = {
  runs?: unknown[] | null;
  sourceResults?: unknown[] | null;
  availableSources?: string[] | null;
  ashbyBoardSlugs?: string[] | null;
};

export type SourceQualityAdvisorItem = {
  source: string;
  displayName: string;
  totalRuns: number;
  successfulRuns: number;
  partialRuns: number;
  failedRuns: number;
  totalProviderRecordsSeen: number;
  totalCandidatesCreated: number;
  totalCandidatesRejected: number;
  totalJobsCreated: number;
  totalJobsExisting: number;
  totalJobsUpdated: number;
  totalJobsEnriched: number;
  totalJobsScored: number;
  totalJobsFailed: number;
  totalWarnings: number;
  averageDurationMs: number | null;
  enrichmentRate: number | null;
  scoringRate: number | null;
  failureRate: number;
  noiseScore: number | null;
  qualityScore: number;
  recommendation: SourceRecommendation;
  recommendationReason: string;
  suggestedCadence: string;
  issues: string[];
  strengths: string[];
};

type MutableAdvisorItem = Omit<
  SourceQualityAdvisorItem,
  | "displayName"
  | "averageDurationMs"
  | "enrichmentRate"
  | "scoringRate"
  | "failureRate"
  | "noiseScore"
  | "qualityScore"
  | "recommendation"
  | "recommendationReason"
  | "suggestedCadence"
  | "issues"
  | "strengths"
> & {
  durationTotalMs: number;
  durationCount: number;
  totalCandidatesFound: number;
  totalCandidatesDeferred: number;
  totalDomainsUnresolved: number;
  totalJobsSkipped: number;
  hnUnsuitable: number;
  hnRemoteUnknown: number;
  hnNotEnriched: number;
};

export function buildSourceQualityAdvisor(input: SourceQualityAdvisorInput | unknown[]) {
  const normalizedInput = Array.isArray(input)
    ? { runs: input, sourceResults: [], availableSources: [] }
    : input;
  const availableSources = normalizedInput.availableSources ?? [];
  const sources = new Set<string>(
    availableSources.filter((source) => typeof source === "string" && Boolean(source.trim())),
  );
  const statsBySource = new Map<string, MutableAdvisorItem>();
  const items = [...(normalizedInput.runs ?? []), ...(normalizedInput.sourceResults ?? [])];

  for (const item of items) {
    const object = objectValue(item);
    if (!object) continue;
    const source = sourceFromItem(object);
    if (!source) continue;
    sources.add(source);
    const stats = getOrCreate(statsBySource, source);
    applyItem(stats, object);
  }

  return Array.from(sources)
    .sort((a, b) => sourceOrder(a) - sourceOrder(b) || a.localeCompare(b))
    .map((source) =>
      finalizeAdvisorItem(
        getOrCreate(statsBySource, source),
        normalizedInput.ashbyBoardSlugs ?? [],
      ),
    );
}

function applyItem(stats: MutableAdvisorItem, item: Record<string, unknown>) {
  const status = stringValue(item.status);
  const duration = durationMs(item);
  const diagnostics = objectValue(item.diagnostics) ?? {};

  stats.totalRuns += 1;
  if (status === "succeeded" || status === "success") stats.successfulRuns += 1;
  if (status === "partial") stats.partialRuns += 1;
  if (status === "failed" || status === "error") stats.failedRuns += 1;
  if (duration !== null) {
    stats.durationTotalMs += duration;
    stats.durationCount += 1;
  }

  stats.totalProviderRecordsSeen += numberValue(item.provider_records_seen) ?? 0;
  stats.totalCandidatesFound += numberValue(item.candidates_found) ?? 0;
  stats.totalCandidatesCreated += numberValue(item.candidates_created) ?? numberValue(item.companies_created) ?? 0;
  stats.totalCandidatesRejected += numberValue(item.candidates_rejected) ?? 0;
  stats.totalCandidatesDeferred += numberValue(item.candidates_deferred) ?? 0;
  stats.totalDomainsUnresolved += numberValue(item.domains_unresolved) ?? 0;
  stats.totalJobsCreated += numberValue(item.jobs_created) ?? 0;
  stats.totalJobsExisting += numberValue(item.jobs_existing) ?? 0;
  stats.totalJobsUpdated += numberValue(item.jobs_updated) ?? 0;
  stats.totalJobsEnriched += numberValue(item.jobs_enriched) ?? 0;
  stats.totalJobsScored += numberValue(item.jobs_scored) ?? 0;
  stats.totalJobsFailed += numberValue(item.jobs_failed) ?? 0;
  stats.totalJobsSkipped += numberValue(item.jobs_skipped) ?? 0;
  stats.totalWarnings += warningCount(item);
  stats.hnUnsuitable += numberValue(diagnostics.h_n_jobs_scored_unsuitable) ?? 0;
  stats.hnRemoteUnknown += numberValue(diagnostics.h_n_jobs_remaining_remote_unknown) ?? 0;
  stats.hnNotEnriched += numberValue(diagnostics.h_n_jobs_not_enriched) ?? 0;
}

function finalizeAdvisorItem(stats: MutableAdvisorItem, ashbyBoardSlugs: string[]): SourceQualityAdvisorItem {
  const jobsAvailable = stats.totalJobsCreated + stats.totalJobsExisting;
  const averageDurationMs =
    stats.durationCount > 0 ? Math.round(stats.durationTotalMs / stats.durationCount) : null;
  const failureRate = stats.totalRuns > 0 ? stats.failedRuns / stats.totalRuns : 0;
  const enrichmentRate = jobsAvailable > 0 ? stats.totalJobsEnriched / jobsAvailable : null;
  const scoringRate = jobsAvailable > 0 ? stats.totalJobsScored / jobsAvailable : null;
  const qualityScore = clampQualityScore(
    computeQualityScore(stats, jobsAvailable, failureRate, enrichmentRate, averageDurationMs),
  );
  const noiseScore = computeNoiseScore(stats);
  const guidance = sourceGuidance(stats.source);
  const issues = [...guidance.issues];
  const strengths = [...guidance.strengths];

  if (stats.totalRuns === 0) issues.push("No recent run history for this source.");
  if (stats.failedRuns > 0) issues.push("Recent failures need a quick look.");
  if (stats.totalWarnings > 0) issues.push("Warnings were reported in recent runs.");
  if (jobsAvailable > 0 && enrichmentRate !== null && enrichmentRate < 0.5) {
    issues.push("Many jobs are not enriched yet.");
  }
  if (stats.totalJobsScored === 0 && stats.totalProviderRecordsSeen > 0) {
    issues.push("Records were seen but no jobs were scored.");
  }
  if (averageDurationMs !== null && averageDurationMs > 90000) {
    issues.push("Runs are slower than the daily loop should prefer.");
  }
  if (stats.source === "ashby" && !ashbyBoardSlugs.length && jobsAvailable === 0) {
    issues.push("Board slugs are required before Ashby can be useful.");
  }
  if (stats.totalJobsScored > 0) strengths.push("Produced scored jobs.");
  if (stats.totalJobsEnriched > 0) strengths.push("Produced enriched jobs.");
  if (jobsAvailable > 0) strengths.push("Created or reused jobs.");

  const recommendation = recommendationFor(stats, {
    ashbyBoardSlugs,
    averageDurationMs,
    failureRate,
    jobsAvailable,
    noiseScore,
    qualityScore,
  });

  return {
    source: stats.source,
    displayName: sourceDisplayName(stats.source),
    totalRuns: stats.totalRuns,
    successfulRuns: stats.successfulRuns,
    partialRuns: stats.partialRuns,
    failedRuns: stats.failedRuns,
    totalProviderRecordsSeen: stats.totalProviderRecordsSeen,
    totalCandidatesCreated: stats.totalCandidatesCreated,
    totalCandidatesRejected: stats.totalCandidatesRejected,
    totalJobsCreated: stats.totalJobsCreated,
    totalJobsExisting: stats.totalJobsExisting,
    totalJobsUpdated: stats.totalJobsUpdated,
    totalJobsEnriched: stats.totalJobsEnriched,
    totalJobsScored: stats.totalJobsScored,
    totalJobsFailed: stats.totalJobsFailed,
    totalWarnings: stats.totalWarnings,
    averageDurationMs,
    enrichmentRate,
    scoringRate,
    failureRate,
    noiseScore,
    qualityScore,
    recommendation,
    recommendationReason: recommendationReason(recommendation, stats.source, qualityScore, noiseScore),
    suggestedCadence: recommendationLabel(recommendation),
    issues: unique(issues).slice(0, 5),
    strengths: unique(strengths).slice(0, 5),
  };
}

function computeQualityScore(
  stats: MutableAdvisorItem,
  jobsAvailable: number,
  failureRate: number,
  enrichmentRate: number | null,
  averageDurationMs: number | null,
) {
  let score = stats.totalRuns > 0 ? 50 : 20;
  if (stats.totalJobsScored > 0) score += 20;
  if (stats.totalJobsEnriched > 0) score += 15;
  if (jobsAvailable > 0) score += 10;
  if (failureRate === 0 && stats.totalRuns > 0) score += 10;
  if (failureRate > 0.25) score -= 15;
  if (stats.totalWarnings > 0) score -= 10;
  if (enrichmentRate !== null && enrichmentRate < 0.5) score -= 10;
  if (averageDurationMs !== null && averageDurationMs > 90000) score -= 10;
  if (stats.totalCandidatesFound > 0 && jobsAvailable / stats.totalCandidatesFound < 0.2) score -= 10;
  if (stats.totalJobsFailed > 0) score -= 10;
  return score;
}

function computeNoiseScore(stats: MutableAdvisorItem) {
  const signal =
    stats.totalCandidatesFound +
    stats.totalCandidatesRejected +
    stats.totalCandidatesDeferred +
    stats.totalWarnings +
    stats.totalJobsFailed +
    stats.totalJobsSkipped +
    stats.hnUnsuitable +
    stats.hnRemoteUnknown +
    stats.hnNotEnriched;
  if (stats.totalRuns === 0 || signal === 0) return null;

  let score = 0;
  score += Math.min(30, stats.totalWarnings * 8);
  score += Math.min(25, stats.totalJobsFailed * 10);
  score += Math.min(25, stats.totalCandidatesDeferred * 3);
  score += Math.min(25, stats.totalCandidatesRejected * 2);
  score += Math.min(20, stats.totalDomainsUnresolved * 3);
  score += Math.min(20, stats.totalJobsSkipped * 3);
  score += Math.min(30, stats.hnUnsuitable * 2 + stats.hnRemoteUnknown + stats.hnNotEnriched * 2);

  const jobsAvailable = stats.totalJobsCreated + stats.totalJobsExisting;
  if (stats.totalCandidatesFound > 0 && jobsAvailable / stats.totalCandidatesFound < 0.25) score += 20;
  return clamp(score);
}

function recommendationFor(
  stats: MutableAdvisorItem,
  context: {
    ashbyBoardSlugs: string[];
    averageDurationMs: number | null;
    failureRate: number;
    jobsAvailable: number;
    noiseScore: number | null;
    qualityScore: number;
  },
): SourceRecommendation {
  if (stats.source === "ashby" && !context.ashbyBoardSlugs.length && context.jobsAvailable === 0) {
    return "needs_configuration";
  }
  if (stats.totalRuns === 0) return "not_enough_data";
  if (stats.failedRuns >= 2 || (context.failureRate > 0.5 && stats.totalRuns >= 2)) return "needs_debugging";
  if (stats.totalProviderRecordsSeen > 0 && stats.totalJobsScored === 0) return "needs_debugging";
  if (["hacker_news", "ashby"].includes(stats.source) && context.qualityScore >= 45 && (context.noiseScore ?? 0) >= 50) {
    return "run_manually";
  }
  if (context.qualityScore >= 75 && context.failureRate <= 0.25 && stats.totalJobsScored > 0) return "run_daily";
  if (context.qualityScore >= 60) return "run_every_few_days";
  if (context.qualityScore >= 45) return "run_weekly";
  if (["hacker_news", "ashby"].includes(stats.source) && context.jobsAvailable > 0) return "run_manually";
  return "not_enough_data";
}

function recommendationReason(
  recommendation: SourceRecommendation,
  source: string,
  qualityScore: number,
  noiseScore: number | null,
) {
  if (recommendation === "needs_configuration") return "Configuration is missing before this source can produce reliable jobs.";
  if (recommendation === "needs_debugging") return "Recent data shows failures or records that are not turning into scored jobs.";
  if (recommendation === "not_enough_data") return "Run this source once or twice before trusting the advisor.";
  if (recommendation === "run_manually") return `${sourceDisplayName(source)} has useful signal, but the noise level is better suited to manual runs.`;
  if (recommendation === "run_daily") return `Strong recent signal with quality ${qualityScore}/100 and low operational noise.`;
  if (recommendation === "run_every_few_days") return `Useful recent signal with quality ${qualityScore}/100.`;
  return `Some useful signal, but noise ${noiseScore ?? "unknown"}/100 makes weekly cadence safer.`;
}

export function recommendationLabel(recommendation: SourceRecommendation) {
  return {
    run_daily: "Run daily",
    run_every_few_days: "Run every few days",
    run_weekly: "Run weekly",
    run_manually: "Run manually",
    needs_configuration: "Needs configuration",
    needs_debugging: "Needs debugging",
    not_enough_data: "Not enough data",
  }[recommendation];
}

function sourceGuidance(source: string) {
  if (source === "hacker_news") {
    return {
      strengths: ["Good for YC/startup hiring signals.", "Good for early-stage companies."],
      issues: ["Noisy source.", "Many roles are founding, senior, onsite, or remote-unknown.", "Needs YC/Ashby enrichment to rank well."],
    };
  }
  if (source === "ycombinator") {
    return {
      strengths: ["Good startup job source.", "High signal for early-stage roles."],
      issues: ["Many roles can be onsite, SF/US-only, or senior.", "Enrichment quality matters."],
    };
  }
  if (source === "ashby") {
    return {
      strengths: ["Excellent when board slugs are known.", "Exact job postings and apply URLs."],
      issues: ["Requires board slugs.", "Company domain may be missing.", "Board expansion can be noisy."],
    };
  }
  if (source === "himalayas") {
    return {
      strengths: ["Structured remote jobs.", "Often clear remote eligibility."],
      issues: ["Broad feeds can still include role mismatch."],
    };
  }
  if (source === "we_work_remotely") {
    return {
      strengths: ["Remote-first source.", "Good broad coverage."],
      issues: ["Broad categories can produce noisy role matches."],
    };
  }
  if (source === "remotive") {
    return {
      strengths: ["Structured remote jobs.", "Useful broad remote source."],
      issues: ["Broad API results still need scoring to separate fit."],
    };
  }
  return { strengths: ["Available discovery source."], issues: ["No source-specific guidance yet."] };
}

function getOrCreate(map: Map<string, MutableAdvisorItem>, source: string) {
  const existing = map.get(source);
  if (existing) return existing;
  const item: MutableAdvisorItem = {
    source,
    totalRuns: 0,
    successfulRuns: 0,
    partialRuns: 0,
    failedRuns: 0,
    totalProviderRecordsSeen: 0,
    totalCandidatesCreated: 0,
    totalCandidatesRejected: 0,
    totalJobsCreated: 0,
    totalJobsExisting: 0,
    totalJobsUpdated: 0,
    totalJobsEnriched: 0,
    totalJobsScored: 0,
    totalJobsFailed: 0,
    totalWarnings: 0,
    durationTotalMs: 0,
    durationCount: 0,
    totalCandidatesFound: 0,
    totalCandidatesDeferred: 0,
    totalDomainsUnresolved: 0,
    totalJobsSkipped: 0,
    hnUnsuitable: 0,
    hnRemoteUnknown: 0,
    hnNotEnriched: 0,
  };
  map.set(source, item);
  return item;
}

function sourceFromItem(item: Record<string, unknown>) {
  return (
    stringValue(item.source) ??
    stringValue(objectValue(item.run)?.source) ??
    stringValue(objectValue(item.source_result)?.source) ??
    firstString(item.sources_planned)
  );
}

function warningCount(item: Record<string, unknown>) {
  if (Array.isArray(item.warnings)) return item.warnings.length;
  return numberValue(item.warning_count) ?? numberValue(item.warnings_count) ?? 0;
}

function durationMs(item: Record<string, unknown>) {
  const explicit = numberValue(item.duration_ms);
  if (explicit !== null) return explicit;
  const started = dateMs(item.started_at);
  const finished = dateMs(item.finished_at);
  if (started === null || finished === null || finished < started) return null;
  return finished - started;
}

function sourceOrder(source: string) {
  const order = ["himalayas", "we_work_remotely", "remotive", "hacker_news", "ycombinator", "ashby"];
  const index = order.indexOf(source);
  return index === -1 ? 999 : index;
}

function unique(values: string[]) {
  return Array.from(new Set(values.filter(Boolean)));
}

function clampQualityScore(value: number) {
  return clamp(Math.round(value));
}

function clamp(value: number) {
  return Math.max(0, Math.min(100, Math.round(value)));
}

function stringValue(value: unknown) {
  return typeof value === "string" && value.trim() ? value : null;
}

function numberValue(value: unknown) {
  if (typeof value === "number" && Number.isFinite(value)) return value;
  if (typeof value === "string" && value.trim()) {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : null;
  }
  return null;
}

function objectValue(value: unknown) {
  return value && typeof value === "object" && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : null;
}

function firstString(value: unknown) {
  return Array.isArray(value)
    ? value.find((item) => typeof item === "string" && Boolean(item.trim())) ?? null
    : null;
}

function dateMs(value: unknown) {
  if (typeof value !== "string" || !value.trim()) return null;
  const parsed = new Date(value).getTime();
  return Number.isNaN(parsed) ? null : parsed;
}

function sourceDisplayName(source: string) {
  return {
    himalayas: "Himalayas",
    we_work_remotely: "We Work Remotely",
    remotive: "Remotive",
    hacker_news: "Hacker News",
    ycombinator: "Y Combinator",
    ashby: "Ashby",
  }[source] ?? source;
}
