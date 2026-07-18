import type { DiscoveryRunListItem, DiscoveryRunsResponse } from "@/types/discovery";

export type DiscoveryRunDetailDisplay = {
  id: string | null;
  source: string;
  sourceMapped: boolean;
  status: string | null;
  startedAt: string | null;
  finishedAt: string | null;
  durationMs: number | null;
  candidatesFound: number | null;
  candidatesNormalized: number | null;
  candidatesDeferred: number | null;
  candidatesRejected: number | null;
  candidatesFailed: number | null;
  companiesCreated: number | null;
  companiesMatched: number | null;
  domainsResolved: number | null;
  domainsUnresolved: number | null;
  jobsCreated: number | null;
  jobsExisting: number | null;
  jobsUpdated: number | null;
  jobsSkipped: number | null;
  jobsEnriched: number | null;
  jobsScored: number | null;
  jobsFailed: number | null;
  error: string | null;
  metadata: Record<string, unknown>;
  warnings: unknown[];
  diagnostics: Record<string, unknown>;
  raw: unknown;
};

export function normalizeDiscoveryRunListResponse(input: unknown): DiscoveryRunsResponse {
  if (Array.isArray(input)) return { items: input as DiscoveryRunListItem[] };
  const object = objectValue(input);
  if (!object) return { items: [] };

  const items =
    arrayValue(object.items) ??
    arrayValue(object.runs) ??
    arrayValue(object.data) ??
    [];

  return {
    ...object,
    items: items as DiscoveryRunListItem[],
  };
}

export function mergeDiscoveryRunDetail(
  row: Record<string, unknown>,
  fetched: unknown,
) {
  const fetchedRun = unwrapDiscoveryRunDetail(fetched);
  const fetchedFields = Object.fromEntries(
    Object.entries(fetchedRun).filter(([, value]) => value !== null && value !== undefined),
  );
  return {
    ...row,
    ...fetchedFields,
    raw: {
      row,
      fetched,
    },
  };
}

export function unwrapDiscoveryRunDetail(input: unknown) {
  const object = objectValue(input);
  if (!object) return {};
  return (
    objectValue(object.run) ??
    objectValue(object.item) ??
    objectValue(object.data) ??
    object
  );
}

export function normalizeDiscoveryRunDetail(
  input: unknown,
  selectedId?: string | null,
): DiscoveryRunDetailDisplay {
  const root = objectValue(input) ?? {};
  const run = objectValue(root.run) ?? {};
  const discoveryRun = objectValue(root.discovery_run) ?? {};
  const sourceResult = objectValue(root.source_result) ?? {};
  const raw = root.raw ?? input;

  const source =
    stringValue(root.source) ??
    stringValue(run.source) ??
    stringValue(discoveryRun.source) ??
    stringValue(sourceResult.source) ??
    firstString(root.sources_planned) ??
    stringValue(objectValue(root.metadata)?.source) ??
    stringValue(objectValue(raw)?.source) ??
    "unknown";

  const startedAt =
    stringValue(root.started_at) ??
    stringValue(root.startedAt) ??
    stringValue(run.started_at) ??
    stringValue(discoveryRun.started_at) ??
    stringValue(sourceResult.started_at);
  const finishedAt =
    stringValue(root.finished_at) ??
    stringValue(root.finishedAt) ??
    stringValue(run.finished_at) ??
    stringValue(discoveryRun.finished_at) ??
    stringValue(sourceResult.finished_at);
  const durationMs =
    firstNumberFrom([root, run, discoveryRun, sourceResult], "duration_ms") ??
    computeDurationMs(startedAt, finishedAt);
  const metadata =
    firstObjectFrom([root, run, discoveryRun], "metadata") ??
    firstObjectFrom([root, run, discoveryRun], "metadata_json") ??
    firstObject([root.diagnostics, sourceResult.diagnostics]) ??
    {};
  const diagnostics = firstObject([root.diagnostics, sourceResult.diagnostics]) ?? {};

  return {
    id:
      stringValue(root.id) ??
      stringValue(run.id) ??
      stringValue(discoveryRun.id) ??
      stringValue(root.discovery_run_id) ??
      stringValue(sourceResult.discovery_run_id) ??
      selectedId ??
      null,
    source,
    sourceMapped: source !== "unknown",
    status:
      stringValue(root.status) ??
      stringValue(run.status) ??
      stringValue(discoveryRun.status) ??
      stringValue(sourceResult.status),
    startedAt,
    finishedAt,
    durationMs,
    candidatesFound:
      firstNumberFrom([root, run, discoveryRun, sourceResult], "candidates_found") ??
      firstNumberFrom([root, run, discoveryRun, sourceResult], "candidates_created"),
    candidatesNormalized: firstNumberFrom([root, run, discoveryRun, sourceResult], "candidates_normalized"),
    candidatesDeferred: firstNumberFrom([root, run, discoveryRun, sourceResult], "candidates_deferred"),
    candidatesRejected: firstNumberFrom([root, run, discoveryRun, sourceResult], "candidates_rejected"),
    candidatesFailed: firstNumberFrom([root, run, discoveryRun, sourceResult], "candidates_failed"),
    companiesCreated: firstNumberFrom([root, run, discoveryRun, sourceResult], "companies_created"),
    companiesMatched: firstNumberFrom([root, run, discoveryRun, sourceResult], "companies_matched"),
    domainsResolved: firstNumberFrom([root, run, discoveryRun, sourceResult], "domains_resolved"),
    domainsUnresolved: firstNumberFrom([root, run, discoveryRun, sourceResult], "domains_unresolved"),
    jobsCreated: firstNumberFrom([root, sourceResult], "jobs_created"),
    jobsExisting: firstNumberFrom([root, sourceResult], "jobs_existing"),
    jobsUpdated: firstNumberFrom([root, sourceResult], "jobs_updated"),
    jobsSkipped: firstNumberFrom([root, sourceResult], "jobs_skipped"),
    jobsEnriched: firstNumberFrom([root, sourceResult], "jobs_enriched"),
    jobsScored: firstNumberFrom([root, sourceResult], "jobs_scored"),
    jobsFailed: firstNumberFrom([root, sourceResult], "jobs_failed"),
    error:
      stringValue(root.error) ??
      stringValue(root.error_message) ??
      stringValue(run.error_message) ??
      stringValue(discoveryRun.error_message) ??
      stringValue(sourceResult.error),
    metadata,
    warnings:
      arrayValue(root.warnings) ??
      arrayValue(run.warnings) ??
      arrayValue(discoveryRun.warnings) ??
      arrayValue(sourceResult.warnings) ??
      [],
    diagnostics,
    raw,
  };
}

function firstNumberFrom(objects: Array<Record<string, unknown>>, key: string) {
  for (const object of objects) {
    const value = numberValue(object[key]);
    if (value !== null) return value;
  }
  return null;
}

function firstObjectFrom(objects: Array<Record<string, unknown>>, key: string) {
  for (const object of objects) {
    const value = objectValue(object[key]);
    if (value) return value;
  }
  return null;
}

function firstObject(values: unknown[]) {
  for (const value of values) {
    const object = objectValue(value);
    if (object) return object;
  }
  return null;
}

function firstString(value: unknown) {
  return Array.isArray(value)
    ? value.find((item) => typeof item === "string" && Boolean(item.trim())) ?? null
    : null;
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

function arrayValue(value: unknown) {
  return Array.isArray(value) ? value : null;
}

function computeDurationMs(startedAt: string | null, finishedAt: string | null) {
  if (!startedAt || !finishedAt) return null;
  const started = new Date(startedAt).getTime();
  const finished = new Date(finishedAt).getTime();
  if (Number.isNaN(started) || Number.isNaN(finished) || finished < started) return null;
  return finished - started;
}
