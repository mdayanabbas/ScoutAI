import type { DiscoveryOptionsState } from "@/components/discovery/DiscoverySourceSelector";
import type { RemoteJobDiscoveryRunRequest } from "@/types/discovery";

export type DiscoveryRunPresetCategory =
  | "daily"
  | "startup_signals"
  | "remote_jobs"
  | "aggressive"
  | "custom";

export type DiscoveryRunPreset = {
  id: string;
  name: string;
  description: string;
  category: DiscoveryRunPresetCategory;
  sources: string[];
  payload: RemoteJobDiscoveryRunRequest;
  isBuiltIn: boolean;
  createdAt: string;
  updatedAt: string;
};

export const discoveryPresetStorageKey = "scoutai.discovery.presets.v1";

const builtInTimestamp = "2026-07-18T00:00:00.000Z";

export const builtInDiscoveryRunPresets: DiscoveryRunPreset[] = [
  {
    id: "remote-jobs-only",
    name: "Remote Jobs Only",
    description: "Run structured remote-job sources with conservative daily-safe defaults.",
    category: "remote_jobs",
    sources: ["himalayas", "we_work_remotely", "remotive"],
    payload: {
      force: true,
      score_after_ingestion: true,
      sources: ["himalayas", "we_work_remotely", "remotive"],
      himalayas: { max_queries: 10, max_pages_per_query: 2 },
      we_work_remotely: { include_all_other: true, max_items_per_feed: 150 },
      remotive: { max_requests: 4, limit_per_request: 200 },
    },
    isBuiltIn: true,
    createdAt: builtInTimestamp,
    updatedAt: builtInTimestamp,
  },
  {
    id: "hn-startup-signals",
    name: "HN Startup Signals",
    description: "Run Hacker News hiring posts for startup signals and enrichment.",
    category: "startup_signals",
    sources: ["hacker_news"],
    payload: {
      force: true,
      score_after_ingestion: true,
      sources: ["hacker_news"],
      hacker_news: {
        feeds: ["jobs"],
        limit: 100,
        lookback_days: 30,
        minimum_score: 0,
        include_items_without_website: true,
        enrich_domains: true,
        ingest_jobs: true,
        enrich_jobs: true,
        score_jobs: true,
      },
    },
    isBuiltIn: true,
    createdAt: builtInTimestamp,
    updatedAt: builtInTimestamp,
  },
  {
    id: "yc-startup-jobs",
    name: "YC Startup Jobs",
    description: "Run Y Combinator startup job discovery and scoring.",
    category: "startup_signals",
    sources: ["ycombinator"],
    payload: {
      force: true,
      score_after_ingestion: true,
      sources: ["ycombinator"],
      ycombinator: {
        max_pages: 5,
        remote_only: false,
        include_recent_only: true,
        lookback_days: 60,
        ingest_jobs: true,
        enrich_jobs: true,
        score_jobs: true,
      },
    },
    isBuiltIn: true,
    createdAt: builtInTimestamp,
    updatedAt: builtInTimestamp,
  },
  {
    id: "yc-hn-startup-signals",
    name: "YC + HN Startup Signals",
    description: "Combine HN company discovery with YC startup jobs.",
    category: "startup_signals",
    sources: ["hacker_news", "ycombinator"],
    payload: {
      force: true,
      score_after_ingestion: true,
      sources: ["hacker_news", "ycombinator"],
      hacker_news: {
        feeds: ["jobs"],
        limit: 100,
        lookback_days: 30,
        minimum_score: 0,
        include_items_without_website: true,
        enrich_domains: true,
        ingest_jobs: true,
        enrich_jobs: true,
        score_jobs: true,
      },
      ycombinator: {
        max_pages: 5,
        remote_only: false,
        include_recent_only: true,
        lookback_days: 60,
        ingest_jobs: true,
        enrich_jobs: true,
        score_jobs: true,
      },
    },
    isBuiltIn: true,
    createdAt: builtInTimestamp,
    updatedAt: builtInTimestamp,
  },
  {
    id: "ashby-board-debug",
    name: "Ashby Board Debug",
    description: "Debug one or more Ashby boards after adding board slugs.",
    category: "startup_signals",
    sources: ["ashby"],
    payload: {
      force: true,
      score_after_ingestion: true,
      sources: ["ashby"],
      ashby: {
        board_slugs: [],
        max_jobs_per_board: 50,
        enrich_jobs: true,
        score_jobs: true,
      },
    },
    isBuiltIn: true,
    createdAt: builtInTimestamp,
    updatedAt: builtInTimestamp,
  },
  {
    id: "aggressive-all-sources",
    name: "Aggressive All Sources",
    description: "Run all non-Ashby sources for broad coverage.",
    category: "aggressive",
    sources: ["himalayas", "we_work_remotely", "remotive", "hacker_news", "ycombinator"],
    payload: {
      force: true,
      score_after_ingestion: true,
      sources: ["himalayas", "we_work_remotely", "remotive", "hacker_news", "ycombinator"],
      himalayas: { max_queries: 10, max_pages_per_query: 2 },
      we_work_remotely: { include_all_other: true, max_items_per_feed: 150 },
      remotive: { max_requests: 4, limit_per_request: 200 },
      hacker_news: {
        feeds: ["jobs"],
        limit: 100,
        lookback_days: 30,
        minimum_score: 0,
        include_items_without_website: true,
        enrich_domains: true,
        ingest_jobs: true,
        enrich_jobs: true,
        score_jobs: true,
      },
      ycombinator: {
        max_pages: 5,
        remote_only: false,
        include_recent_only: true,
        lookback_days: 60,
        ingest_jobs: true,
        enrich_jobs: true,
        score_jobs: true,
      },
    },
    isBuiltIn: true,
    createdAt: builtInTimestamp,
    updatedAt: builtInTimestamp,
  },
];

export const discoveryPresetStorage = {
  getCustomPresets,
  saveCustomPreset,
  updateCustomPreset,
  deleteCustomPreset,
  getAllPresets,
  duplicatePreset,
};

export function getCustomPresets(): DiscoveryRunPreset[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = window.localStorage.getItem(discoveryPresetStorageKey);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) return [];
    return parsed.filter(isPreset).map((preset) => ({ ...preset, isBuiltIn: false }));
  } catch {
    return [];
  }
}

export function saveCustomPreset(preset: Omit<DiscoveryRunPreset, "id" | "isBuiltIn" | "createdAt" | "updatedAt">) {
  const now = new Date().toISOString();
  const created: DiscoveryRunPreset = {
    ...preset,
    id: createPresetId(preset.name),
    isBuiltIn: false,
    createdAt: now,
    updatedAt: now,
  };
  writeCustomPresets([...getCustomPresets(), created]);
  return created;
}

export function updateCustomPreset(presetId: string, changes: Partial<DiscoveryRunPreset>) {
  const presets = getCustomPresets();
  const next = presets.map((preset) =>
    preset.id === presetId
      ? {
          ...preset,
          ...changes,
          id: preset.id,
          isBuiltIn: false,
          createdAt: preset.createdAt,
          updatedAt: new Date().toISOString(),
        }
      : preset,
  );
  writeCustomPresets(next);
  return next.find((preset) => preset.id === presetId) ?? null;
}

export function deleteCustomPreset(presetId: string) {
  writeCustomPresets(getCustomPresets().filter((preset) => preset.id !== presetId));
}

export function getAllPresets() {
  return [...builtInDiscoveryRunPresets, ...getCustomPresets()];
}

export function duplicatePreset(presetId: string) {
  const preset = getAllPresets().find((item) => item.id === presetId);
  if (!preset) return null;
  return saveCustomPreset({
    name: `${preset.name} Copy`,
    description: preset.description,
    category: "custom",
    sources: [...preset.sources],
    payload: deepClone(preset.payload),
  });
}

export function materializePresetPayload(
  preset: DiscoveryRunPreset,
  options: DiscoveryOptionsState,
) {
  const payload = deepClone(preset.payload);
  const ashbyBoardSlugs = parseBoardSlugs(options.ashby.board_slugs_text);
  const sources = Array.isArray(payload.sources) ? [...payload.sources] : [...preset.sources];

  if (preset.id === "aggressive-all-sources" && ashbyBoardSlugs.length && !sources.includes("ashby")) {
    sources.push("ashby");
  }

  if (sources.includes("ashby")) {
    payload.ashby = {
      ...(payload.ashby ?? {}),
      board_slugs: Array.isArray(payload.ashby?.board_slugs) && payload.ashby.board_slugs.length
        ? payload.ashby.board_slugs
        : ashbyBoardSlugs,
      max_jobs_per_board: payload.ashby?.max_jobs_per_board ?? 50,
      enrich_jobs: payload.ashby?.enrich_jobs ?? true,
      score_jobs: payload.ashby?.score_jobs ?? true,
      enabled: true,
    };
  }

  payload.force = true;
  payload.score_after_ingestion = true;
  payload.sources = sources.filter((source) => source !== "ashby" || (payload.ashby?.board_slugs?.length ?? 0) > 0 || preset.id === "ashby-board-debug");
  return payload;
}

export function presetNeedsConfiguration(
  preset: DiscoveryRunPreset,
  options: DiscoveryOptionsState,
) {
  const payload = materializePresetPayload(preset, options);
  return Boolean(payload.sources?.includes("ashby") && !(payload.ashby?.board_slugs?.length));
}

export function payloadToOptions(
  payload: RemoteJobDiscoveryRunRequest,
  currentOptions: DiscoveryOptionsState,
): DiscoveryOptionsState {
  return {
    himalayas: payload.himalayas ?? currentOptions.himalayas,
    we_work_remotely: payload.we_work_remotely ?? currentOptions.we_work_remotely,
    remotive: payload.remotive ?? currentOptions.remotive,
    hacker_news: payload.hacker_news ?? currentOptions.hacker_news,
    ycombinator: payload.ycombinator ?? currentOptions.ycombinator,
    ashby: {
      ...(payload.ashby ?? currentOptions.ashby),
      board_slugs_text: (payload.ashby?.board_slugs ?? parseBoardSlugs(currentOptions.ashby.board_slugs_text)).join(", "),
    },
  };
}

function writeCustomPresets(presets: DiscoveryRunPreset[]) {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(discoveryPresetStorageKey, JSON.stringify(presets));
  } catch {
    // localStorage can be unavailable in private contexts; callers refresh from storage safely.
  }
}

function isPreset(value: unknown): value is DiscoveryRunPreset {
  if (!value || typeof value !== "object") return false;
  const preset = value as DiscoveryRunPreset;
  return Boolean(
    typeof preset.id === "string" &&
      typeof preset.name === "string" &&
      Array.isArray(preset.sources) &&
      preset.payload &&
      typeof preset.payload === "object",
  );
}

function createPresetId(name: string) {
  const slug = name.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/(^-|-$)/g, "");
  return `custom-${slug || "preset"}-${Date.now()}`;
}

function parseBoardSlugs(value?: string | null) {
  return (value ?? "")
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

function deepClone<T>(value: T): T {
  return JSON.parse(JSON.stringify(value)) as T;
}
