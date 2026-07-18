import type { DiscoveryOptionsState } from "@/components/discovery/DiscoverySourceSelector";
import type { SourceQualityAdvisorItem } from "@/lib/source-quality-advisor";
import type { RemoteJobDiscoveryRunRequest } from "@/types/discovery";

export const safeDefaultDailySources = ["himalayas", "we_work_remotely", "remotive"];

export type DailyScoutPayloadResult = {
  payload: RemoteJobDiscoveryRunRequest;
  selectedSources: string[];
  fallbackReason: string | null;
  riskyWarnings: string[];
};

export function buildDailyScoutPayload({
  advisors,
  options,
  availableSources,
  includeWeeklyManualSources = false,
  manualSources,
}: {
  advisors: SourceQualityAdvisorItem[];
  options: DiscoveryOptionsState;
  availableSources: string[];
  includeWeeklyManualSources?: boolean;
  manualSources?: string[] | null;
}): DailyScoutPayloadResult {
  const available = new Set(availableSources);
  const ashbyBoardSlugs = parseBoardSlugs(options.ashby.board_slugs_text);
  let fallbackReason: string | null = null;
  let selectedSources = manualSources?.length
    ? manualSources
    : advisors
        .filter((advisor) =>
          ["run_daily", "run_every_few_days"].includes(advisor.recommendation) ||
          (includeWeeklyManualSources &&
            ["run_weekly", "run_manually"].includes(advisor.recommendation)),
        )
        .filter((advisor) => !["needs_configuration", "needs_debugging", "not_enough_data"].includes(advisor.recommendation))
        .map((advisor) => advisor.source);

  if (!manualSources?.length) {
    const hasEnoughAdvisorData = advisors.some((advisor) => advisor.totalRuns > 0);
    if (!hasEnoughAdvisorData) {
      fallbackReason = "Not enough source history yet. Using safe remote-job sources.";
      selectedSources = safeDefaultDailySources;
    } else if (!selectedSources.length) {
      fallbackReason = "No strong daily source set yet. Using safe remote-job sources.";
      selectedSources = safeDefaultDailySources;
    }
  }

  selectedSources = unique(
    selectedSources.filter((source) => available.has(source) || manualSources?.includes(source)),
  );
  if (selectedSources.includes("ashby") && !ashbyBoardSlugs.length) {
    selectedSources = selectedSources.filter((source) => source !== "ashby");
  }

  const payload: RemoteJobDiscoveryRunRequest = {
    force: true,
    score_after_ingestion: true,
    sources: selectedSources,
  };

  if (selectedSources.includes("himalayas")) {
    payload.himalayas = {
      max_queries: options.himalayas.max_queries ?? 10,
      max_pages_per_query: options.himalayas.max_pages_per_query ?? 2,
    };
  }
  if (selectedSources.includes("we_work_remotely")) {
    payload.we_work_remotely = {
      include_all_other: options.we_work_remotely.include_all_other ?? true,
      max_items_per_feed: options.we_work_remotely.max_items_per_feed ?? 150,
    };
  }
  if (selectedSources.includes("remotive")) {
    payload.remotive = {
      max_requests: options.remotive.max_requests ?? 4,
      limit_per_request: options.remotive.limit_per_request ?? 200,
    };
  }
  if (selectedSources.includes("hacker_news")) {
    payload.hacker_news = {
      feeds: options.hacker_news.feeds ?? ["jobs"],
      limit: options.hacker_news.limit ?? 100,
      lookback_days: options.hacker_news.lookback_days ?? 30,
      minimum_score: options.hacker_news.minimum_score ?? 0,
      include_items_without_website: options.hacker_news.include_items_without_website ?? true,
      enrich_domains: options.hacker_news.enrich_domains ?? true,
      ingest_jobs: options.hacker_news.ingest_jobs ?? true,
      enrich_jobs: options.hacker_news.enrich_jobs ?? true,
      score_jobs: options.hacker_news.score_jobs ?? true,
      enabled: true,
    };
  }
  if (selectedSources.includes("ycombinator")) {
    payload.ycombinator = {
      max_pages: options.ycombinator.max_pages ?? 5,
      remote_only: options.ycombinator.remote_only ?? false,
      include_recent_only: options.ycombinator.include_recent_only ?? true,
      lookback_days: options.ycombinator.lookback_days ?? 60,
      ingest_jobs: options.ycombinator.ingest_jobs ?? true,
      enrich_jobs: options.ycombinator.enrich_jobs ?? true,
      score_jobs: options.ycombinator.score_jobs ?? true,
      enabled: true,
    };
  }
  if (selectedSources.includes("ashby") && ashbyBoardSlugs.length) {
    payload.ashby = {
      board_slugs: ashbyBoardSlugs,
      max_jobs_per_board: options.ashby.max_jobs_per_board ?? 50,
      enrich_jobs: options.ashby.enrich_jobs ?? true,
      score_jobs: options.ashby.score_jobs ?? true,
      enabled: true,
    };
  }

  return {
    payload,
    selectedSources,
    fallbackReason,
    riskyWarnings: riskyWarnings(selectedSources, advisors, ashbyBoardSlugs),
  };
}

function riskyWarnings(
  selectedSources: string[],
  advisors: SourceQualityAdvisorItem[],
  ashbyBoardSlugs: string[],
) {
  const warnings: string[] = [];
  for (const source of selectedSources) {
    const advisor = advisors.find((item) => item.source === source);
    if (source === "hacker_news" && (advisor?.noiseScore ?? 0) >= 50) {
      warnings.push("Hacker News is currently noisy. Expect more manual review.");
    }
    if (source === "ashby" && !ashbyBoardSlugs.length) {
      warnings.push("Ashby requires board slugs before it can run.");
    }
    if (source === "ycombinator" && (advisor?.failedRuns ?? 0) >= 2) {
      warnings.push("Y Combinator has repeated failures in recent history.");
    }
    if (advisor?.recommendation === "needs_debugging") {
      warnings.push(`${advisor.displayName} needs debugging before it is a good daily source.`);
    }
  }
  return unique(warnings);
}

function parseBoardSlugs(value?: string | null) {
  return (value ?? "")
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

function unique(values: string[]) {
  return Array.from(new Set(values));
}
