export type SourceEffectivenessInput = Record<string, unknown>;

export type SourceEffectivenessStats = {
  source: string;
  total_runs: number;
  successful_runs: number;
  partial_runs: number;
  failed_runs: number;
  total_candidates: number;
  total_jobs_created: number;
  total_jobs_existing: number;
  total_jobs_scored: number;
  total_jobs_failed: number;
  average_duration_ms: number | null;
  enrichment_rate: number | null;
  failure_rate: number;
  warning_count: number;
};

export type SourceEffectivenessSummary = {
  sources: SourceEffectivenessStats[];
  best_volume_source: SourceEffectivenessStats | null;
  best_enrichment_source: SourceEffectivenessStats | null;
  fastest_source: SourceEffectivenessStats | null;
  noisiest_source: SourceEffectivenessStats | null;
  most_failure_prone_source: SourceEffectivenessStats | null;
};

type MutableStats = SourceEffectivenessStats & {
  duration_total_ms: number;
  duration_count: number;
  total_jobs_enriched: number;
};

export function buildSourceEffectivenessSummary(
  runsOrSourceResults: SourceEffectivenessInput[] | null | undefined,
): SourceEffectivenessSummary {
  const bySource = new Map<string, MutableStats>();

  for (const item of runsOrSourceResults ?? []) {
    const source = stringValue(item.source) ?? "unknown";
    const stats = getOrCreateStats(bySource, source);
    const status = stringValue(item.status);
    const duration = durationMs(item);

    stats.total_runs += 1;
    if (status === "succeeded" || status === "success") stats.successful_runs += 1;
    if (status === "partial") stats.partial_runs += 1;
    if (status === "failed" || status === "error") stats.failed_runs += 1;
    if (duration !== null) {
      stats.duration_total_ms += duration;
      stats.duration_count += 1;
    }

    stats.total_candidates += firstNumber(item, [
      "candidates_found",
      "candidates_created",
      "total_candidates_created",
    ]);
    stats.total_jobs_created += firstNumber(item, ["jobs_created", "total_jobs_created"]);
    stats.total_jobs_existing += firstNumber(item, ["jobs_existing", "total_jobs_existing"]);
    stats.total_jobs_scored += firstNumber(item, ["jobs_scored", "total_jobs_scored"]);
    stats.total_jobs_failed += firstNumber(item, ["jobs_failed", "total_jobs_failed"]);
    stats.total_jobs_enriched += firstNumber(item, ["jobs_enriched", "total_jobs_enriched"]);
    stats.warning_count += warningCount(item);
  }

  const sources = Array.from(bySource.values())
    .map((stats) => {
      const jobsAvailable = stats.total_jobs_created + stats.total_jobs_existing;
      return {
        ...stats,
        average_duration_ms:
          stats.duration_count > 0
            ? Math.round(stats.duration_total_ms / stats.duration_count)
            : null,
        enrichment_rate:
          jobsAvailable > 0 ? stats.total_jobs_enriched / jobsAvailable : null,
        failure_rate: stats.total_runs > 0 ? stats.failed_runs / stats.total_runs : 0,
      };
    })
    .sort((a, b) => a.source.localeCompare(b.source));

  return {
    sources,
    best_volume_source: maxBy(sources, (stats) =>
      stats.total_candidates + stats.total_jobs_created + stats.total_jobs_existing,
    ),
    best_enrichment_source: maxBy(
      sources.filter((stats) => stats.enrichment_rate !== null),
      (stats) => stats.enrichment_rate ?? 0,
    ),
    fastest_source: minBy(
      sources.filter((stats) => stats.average_duration_ms !== null),
      (stats) => stats.average_duration_ms ?? Number.MAX_SAFE_INTEGER,
    ),
    noisiest_source: maxBy(sources, (stats) => stats.warning_count + stats.total_jobs_failed),
    most_failure_prone_source: maxBy(sources, (stats) => stats.failure_rate),
  };
}

function getOrCreateStats(map: Map<string, MutableStats>, source: string) {
  const existing = map.get(source);
  if (existing) return existing;

  const created: MutableStats = {
    source,
    total_runs: 0,
    successful_runs: 0,
    partial_runs: 0,
    failed_runs: 0,
    total_candidates: 0,
    total_jobs_created: 0,
    total_jobs_existing: 0,
    total_jobs_scored: 0,
    total_jobs_failed: 0,
    average_duration_ms: null,
    enrichment_rate: null,
    failure_rate: 0,
    warning_count: 0,
    duration_total_ms: 0,
    duration_count: 0,
    total_jobs_enriched: 0,
  };
  map.set(source, created);
  return created;
}

function firstNumber(item: SourceEffectivenessInput, keys: string[]) {
  for (const key of keys) {
    const value = numberValue(item[key]);
    if (value !== null) return value;
  }
  return 0;
}

function warningCount(item: SourceEffectivenessInput) {
  if (Array.isArray(item.warnings)) return item.warnings.length;
  return firstNumber(item, ["warning_count", "warnings_count"]);
}

function durationMs(item: SourceEffectivenessInput) {
  const explicit = numberValue(item.duration_ms);
  if (explicit !== null) return explicit;

  const startedAt = dateMs(item.started_at);
  const finishedAt = dateMs(item.finished_at);
  if (startedAt === null || finishedAt === null || finishedAt < startedAt) return null;
  return finishedAt - startedAt;
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

function dateMs(value: unknown) {
  if (typeof value !== "string" || !value.trim()) return null;
  const parsed = new Date(value).getTime();
  return Number.isNaN(parsed) ? null : parsed;
}

function maxBy<T>(items: T[], selector: (item: T) => number) {
  let best: T | null = null;
  let bestValue = 0;
  for (const item of items) {
    const value = selector(item);
    if (best === null || value > bestValue) {
      best = item;
      bestValue = value;
    }
  }
  return bestValue > 0 ? best : null;
}

function minBy<T>(items: T[], selector: (item: T) => number) {
  let best: T | null = null;
  let bestValue = Number.MAX_SAFE_INTEGER;
  for (const item of items) {
    const value = selector(item);
    if (value < bestValue) {
      best = item;
      bestValue = value;
    }
  }
  return best;
}
