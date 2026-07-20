"use client";

import Link from "next/link";
import { useEffect, useMemo, useState, type ReactNode } from "react";
import { useQuery } from "@tanstack/react-query";

import {
  DailyScoutNextActions,
  DailyScoutPanel,
  PayloadPreviewDrawer,
} from "@/components/discovery/DailyScoutPanel";
import { DailyScoutReviewQueue } from "@/components/discovery/DailyScoutReviewQueue";
import { DailyScoutRunResult } from "@/components/discovery/DailyScoutRunResult";
import {
  DiscoveryRunPresets,
  type PresetFormData,
  type PresetRunSessionItem,
} from "@/components/discovery/DiscoveryRunPresets";
import {
  DiscoverySourceSelector,
  type DiscoveryOptionsState,
} from "@/components/discovery/DiscoverySourceSelector";
import { DiscoveryRunComparison } from "@/components/discovery/DiscoveryRunComparison";
import { DiscoveryRunDetailDrawer } from "@/components/discovery/DiscoveryRunDetailDrawer";
import { DiscoveryRunHistory } from "@/components/discovery/DiscoveryRunHistory";
import { DiscoveryRunSummary } from "@/components/discovery/DiscoveryRunSummary";
import { DiscoverySourceEffectiveness } from "@/components/discovery/DiscoverySourceEffectiveness";
import { DiscoverySourceResultCard } from "@/components/discovery/DiscoverySourceResultCard";
import { DiscoveryTopRecommendations } from "@/components/discovery/DiscoveryTopRecommendations";
import { SourceQualityAdvisor } from "@/components/discovery/SourceQualityAdvisor";
import { PageHeader } from "@/components/layout/PageHeader";
import { buildSourceEffectivenessSummary } from "@/lib/discovery-effectiveness";
import { mergeDiscoveryRunDetail } from "@/lib/discovery-run-normalization";
import {
  buildDailyScoutReviewQueue,
  getDailyScoutReviewState,
  reviewStatusFromDecisionStatus,
  upsertDailyScoutReviewState,
  type DailyScoutReviewItem,
  type DailyScoutReviewState,
  type DailyScoutReviewStatus,
} from "@/lib/daily-scout-review-queue";
import {
  cacheEntryToReviewFields,
  deriveResumeFitFromPacket,
  getResumeFitCache,
  upsertResumeFitCache,
  type ResumeFitCacheEntry,
  type ResumeFitResult,
} from "@/lib/resume-aware-review-ranking";
import {
  discoveryPresetStorage,
  getAllPresets,
  materializePresetPayload,
  payloadToOptions,
  presetNeedsConfiguration,
  type DiscoveryRunPreset,
} from "@/lib/discovery-presets";
import { buildDailyScoutPayload, safeDefaultDailySources } from "@/lib/daily-scout";
import { buildSourceQualityAdvisor } from "@/lib/source-quality-advisor";
import { watchCompanyFromJob } from "@/lib/company-watchlist-api";
import {
  fetchDiscoveryRun,
  fetchDiscoveryRuns,
  fetchRemoteDiscoveryPlan,
  runRemoteJobDiscovery,
} from "@/lib/discovery-api";
import { listJobDecisions, saveJobDecision, updateJobDecision } from "@/lib/job-decisions-api";
import { fetchRecommendedJobMatches } from "@/lib/job-matches-api";
import { fetchCompanyWatchlist } from "@/lib/company-watchlist-api";
import { fetchActiveResume } from "@/lib/resumes-api";
import { generateApplicationPacketForJob } from "@/lib/application-packet-api";
import { generateResumeImprovementForJob } from "@/lib/resume-improvements-api";
import type {
  DiscoveryRunListItem,
  DiscoverySource,
  RemoteDiscoverySourceResult,
  RemoteJobDiscoveryOrchestratorResult,
  RemoteJobDiscoveryRunRequest,
} from "@/types/discovery";
import type { JobApplicationDecisionResponse, JobDecisionStatus } from "@/types/job-decision";

type DiscoveryRunDetailRow = DiscoveryRunListItem | RemoteDiscoverySourceResult;

const fallbackSources = [
  "himalayas",
  "we_work_remotely",
  "remotive",
  "hacker_news",
  "ycombinator",
  "ashby",
];
const defaultSelected = ["himalayas", "we_work_remotely", "remotive"];
const dailyScoutPhases = [
  "Selecting sources",
  "Running discovery",
  "Enriching jobs",
  "Scoring matches",
  "Preparing recommendations",
];

const defaultOptions: DiscoveryOptionsState = {
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
  ashby: {
    board_slugs_text: "",
    max_jobs_per_board: 50,
    enrich_jobs: true,
    score_jobs: true,
  },
};

export default function DiscoveryControlCenterPage() {
  const [selectedSources, setSelectedSources] = useState<string[]>(defaultSelected);
  const [options, setOptions] = useState<DiscoveryOptionsState>(defaultOptions);
  const [force, setForce] = useState(true);
  const [scoreAfterIngestion, setScoreAfterIngestion] = useState(true);
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState<RemoteJobDiscoveryOrchestratorResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [detailsRunId, setDetailsRunId] = useState<string | null>(null);
  const [detailsRun, setDetailsRun] = useState<Record<string, unknown> | null>(null);
  const [detailsError, setDetailsError] = useState<string | null>(null);
  const [selectedRunIds, setSelectedRunIds] = useState<string[]>([]);
  const [compareOpen, setCompareOpen] = useState(false);
  const [compareMessage, setCompareMessage] = useState<string | null>(null);
  const [rerunMessage, setRerunMessage] = useState<string | null>(null);
  const [includeWeeklyManualSources, setIncludeWeeklyManualSources] = useState(false);
  const [dailyRunning, setDailyRunning] = useState(false);
  const [dailyPhaseIndex, setDailyPhaseIndex] = useState(0);
  const [dailyResult, setDailyResult] = useState<RemoteJobDiscoveryOrchestratorResult | null>(null);
  const [showPayloadPreview, setShowPayloadPreview] = useState(false);
  const [copyMessage, setCopyMessage] = useState<string | null>(null);
  const [payloadCopied, setPayloadCopied] = useState(false);
  const [presets, setPresets] = useState<DiscoveryRunPreset[]>([]);
  const [presetMessage, setPresetMessage] = useState<string | null>(null);
  const [presetSessionRuns, setPresetSessionRuns] = useState<PresetRunSessionItem[]>([]);
  const [reviewState, setReviewState] = useState<DailyScoutReviewState[]>([]);
  const [decisionOverrides, setDecisionOverrides] = useState<Record<string, JobApplicationDecisionResponse>>({});
  const [watchOverrides, setWatchOverrides] = useState<Record<string, string>>({});
  const [includeSkippedReviewItems, setIncludeSkippedReviewItems] = useState(false);
  const [reviewMessage, setReviewMessage] = useState<string | null>(null);
  const [reviewError, setReviewError] = useState<string | null>(null);
  const [resumeFitCache, setResumeFitCache] = useState<ResumeFitCacheEntry[]>([]);
  const [resumeFitOverrides, setResumeFitOverrides] = useState<Record<string, ResumeFitResult>>({});
  const [resumeRankLoading, setResumeRankLoading] = useState(false);
  const [resumeRankMessage, setResumeRankMessage] = useState<string | null>(null);
  const [resumeRankError, setResumeRankError] = useState<string | null>(null);

  const planQuery = useQuery({
    queryKey: ["remote-discovery-plan"],
    queryFn: fetchRemoteDiscoveryPlan,
    retry: 1,
  });
  const runsQuery = useQuery({
    queryKey: ["discovery-runs", "recent"],
    queryFn: () => fetchDiscoveryRuns({ limit: 25 }),
    retry: 1,
  });
  const decisionsQuery = useQuery({
    queryKey: ["job-decisions", "daily-scout-review"],
    queryFn: () => listJobDecisions({ limit: 100, include_archived: true }),
    retry: 1,
    enabled: Boolean(dailyResult),
  });
  const watchlistQuery = useQuery({
    queryKey: ["company-watchlist", "daily-scout-review"],
    queryFn: () => fetchCompanyWatchlist({ limit: 100 }),
    retry: 1,
    enabled: Boolean(dailyResult),
  });
  const fallbackMatchesQuery = useQuery({
    queryKey: ["job-matches", "daily-scout-review-fallback"],
    queryFn: () => fetchRecommendedJobMatches({ order_by: "recommended", limit: 100 }),
    retry: 1,
    enabled: Boolean(dailyResult && !(dailyResult.top_recommendations ?? []).length),
  });
  const activeResumeQuery = useQuery({
    queryKey: ["active-resume", "daily-scout-review"],
    queryFn: fetchActiveResume,
    retry: 1,
    enabled: Boolean(dailyResult),
  });

  useEffect(() => {
    if (!dailyRunning) {
      setDailyPhaseIndex(0);
      return;
    }
    const interval = window.setInterval(() => {
      setDailyPhaseIndex((current) => Math.min(current + 1, dailyScoutPhases.length - 1));
    }, 1400);
    return () => window.clearInterval(interval);
  }, [dailyRunning]);

  useEffect(() => {
    setPresets(getAllPresets());
    setReviewState(getDailyScoutReviewState());
    setResumeFitCache(getResumeFitCache());
  }, []);

  useEffect(() => {
    if (!dailyResult) return;
    if (window.location.hash === "#review-queue" || window.location.search.includes("tab=review")) {
      window.setTimeout(() => {
        document.getElementById("review-queue")?.scrollIntoView({ behavior: "smooth", block: "start" });
      }, 100);
    }
  }, [dailyResult]);

  const availableSources = useMemo(
    () =>
      (planQuery.data?.available_sources ?? [])
        .map((item) => item.source)
        .filter((source): source is DiscoverySource => Boolean(source)).length
        ? (planQuery.data?.available_sources ?? [])
            .map((item) => item.source)
            .filter((source): source is DiscoverySource => Boolean(source))
        : fallbackSources,
    [planQuery.data?.available_sources],
  );

  function toggleSource(source: string) {
    setSelectedSources((current) =>
      current.includes(source)
        ? current.filter((item) => item !== source)
        : [...current, source],
    );
  }

  async function runPayload(payload: RemoteJobDiscoveryRunRequest) {
    setRunning(true);
    setError(null);
    setResult(null);
    setRerunMessage(null);
    setDailyResult(null);
    try {
      const response = await runRemoteJobDiscovery(payload);
      setResult(response);
      await runsQuery.refetch();
      return response;
    } catch (err) {
      setError(friendlyError(err));
      return null;
    } finally {
      setRunning(false);
    }
  }

  function runSelected() {
    return runPayload(buildPayload(selectedSources, options, force, scoreAfterIngestion));
  }

  async function openRunDetails(run: DiscoveryRunDetailRow) {
    const row = { ...run };
    const runId = detailRunId(row);
    if (!runId) {
      setDetailsRunId(null);
      setDetailsRun(row);
      setDetailsError("This run does not include an ID for backend details.");
      return;
    }

    setDetailsRunId(runId);
    setDetailsRun(row);
    setDetailsError(null);
    try {
      const details = await fetchDiscoveryRun(runId);
      setDetailsRun(mergeDiscoveryRunDetail(row, details));
    } catch (err) {
      setDetailsError(friendlyError(err));
    }
  }

  function closeRunDetails() {
    setDetailsRunId(null);
    setDetailsRun(null);
    setDetailsError(null);
  }

  function toggleCompareRun(runId: string) {
    setSelectedRunIds((current) => {
      if (current.includes(runId)) return current.filter((id) => id !== runId);
      if (current.length >= 5) return current;
      return [...current, runId];
    });
    setCompareMessage(null);
  }

  function compareRuns() {
    if (selectedRunIds.length < 2) {
      setCompareMessage("Select 2 to 5 runs to compare.");
      return;
    }
    setCompareOpen(true);
    setCompareMessage(null);
  }

  function rerunSource(run: DiscoveryRunListItem) {
    const source = stringValue(run.source);
    if (!source) {
      setRerunMessage("This run does not include a source to re-run.");
      return;
    }

    const payload = buildRerunPayload(source, run, options);
    if (!payload) {
      setRerunMessage("Ashby requires board slugs. Use the source options form above.");
      return;
    }

    setRerunMessage(`Re-running ${source} with the previous source scope.`);
    void runPayload(payload);
  }

  async function runDailyScout() {
    if (dailyPayload.riskyWarnings.length) {
      const confirmed = window.confirm(
        `Daily Scout includes sources with warnings:\n\n${dailyPayload.riskyWarnings.join("\n")}\n\nRun anyway?`,
      );
      if (!confirmed) return;
    }

    setDailyRunning(true);
    setDailyResult(null);
    const response = await runPayload(dailyPayload.payload);
    if (response) setDailyResult(response);
    setDailyRunning(false);
  }

  async function copyPayload() {
    setCopyMessage(null);
    setPayloadCopied(false);
    try {
      await navigator.clipboard.writeText(JSON.stringify(dailyPayload.payload, null, 2));
      setPayloadCopied(true);
    } catch {
      setCopyMessage("Could not copy payload. You can still select and copy the JSON manually.");
    }
  }

  async function runPreset(preset: DiscoveryRunPreset) {
    setPresetMessage(null);
    if (presetNeedsConfiguration(preset, options)) {
      setPresetMessage("This preset needs Ashby board slugs before running.");
      return;
    }

    const startedAt = new Date().toISOString();
    const payload = materializePresetPayload(preset, options);
    const started = Date.now();
    const response = await runPayload(payload);
    if (!response) return;

    setPresetSessionRuns((current) => [
      {
        presetId: preset.id,
        presetName: preset.name,
        startedAt,
        status: response.status ?? "unknown",
        duration: Date.now() - started,
        sources: payload.sources ?? preset.sources,
        jobsScored: response.total_jobs_scored ?? 0,
        warningsCount: response.warnings?.length ?? 0,
      },
      ...current,
    ]);
  }

  function applyPreset(preset: DiscoveryRunPreset) {
    const payload = materializePresetPayload(preset, options);
    setSelectedSources(payload.sources ?? preset.sources);
    setOptions(payloadToOptions(payload, options));
    setPresetMessage("Preset applied. Review options, then run discovery.");
  }

  function saveCurrentPreset(data: PresetFormData) {
    discoveryPresetStorage.saveCustomPreset({
      name: data.name,
      description: data.description,
      category: data.category,
      sources: data.payload.sources ?? [],
      payload: data.payload,
    });
    setPresets(getAllPresets());
    setPresetMessage("Preset saved.");
  }

  function updatePreset(preset: DiscoveryRunPreset, data: PresetFormData) {
    discoveryPresetStorage.updateCustomPreset(preset.id, {
      name: data.name,
      description: data.description,
      category: data.category,
      sources: data.payload.sources ?? [],
      payload: data.payload,
    });
    setPresets(getAllPresets());
    setPresetMessage("Preset updated.");
  }

  function duplicatePreset(preset: DiscoveryRunPreset) {
    discoveryPresetStorage.duplicatePreset(preset.id);
    setPresets(getAllPresets());
    setPresetMessage("Preset duplicated.");
  }

  function deletePreset(preset: DiscoveryRunPreset) {
    discoveryPresetStorage.deleteCustomPreset(preset.id);
    setPresets(getAllPresets());
    setPresetMessage("Preset deleted.");
  }

  async function applyReviewDecision(
    item: DailyScoutReviewItem,
    status: JobDecisionStatus,
    reviewStatus: DailyScoutReviewStatus,
  ) {
    if (!item.job_id) {
      setReviewError("This queue item is missing a job ID.");
      return;
    }
    setReviewError(null);
    setReviewMessage(null);
    try {
      const response = item.decision_id
        ? await updateJobDecision(item.decision_id, { decision_status: status, priority: "medium" })
        : await saveJobDecision(item.job_id, { decision_status: status, priority: "medium" });
      setDecisionOverrides((current) => ({ ...current, [item.job_id]: response }));
      setReviewState((current) => upsertDailyScoutReviewState(current, item.job_id, reviewStatusFromDecisionStatus(status)));
      setReviewMessage(`${item.title} marked as ${statusLabel(status)}.`);
      await decisionsQuery.refetch();
    } catch (err) {
      setReviewError(friendlyError(err));
    }
  }

  async function watchCompany(item: DailyScoutReviewItem) {
    if (!item.job_id) {
      setReviewError("This queue item is missing a job ID.");
      return;
    }
    setReviewError(null);
    setReviewMessage(null);
    try {
      await watchCompanyFromJob(item.job_id, {
        priority: "medium",
        watch_status: "watching",
        interest_reason: `Daily Scout found ${item.title}${item.company_name ? ` at ${item.company_name}` : ""}.`,
        target_roles: item.title ? [item.title] : [],
        tags: ["daily-scout"],
        remote_interest: remoteInterest(item.remote_eligibility),
        junior_friendliness_signal: juniorSignal(item.title, item.eligibility_reason),
      });
      setWatchOverrides((current) => ({ ...current, [item.job_id]: "watching" }));
      setReviewState((current) => upsertDailyScoutReviewState(current, item.job_id, "watched_company"));
      setReviewMessage(item.company_name ? `${item.company_name} added to watchlist.` : "Company added to watchlist.");
      await watchlistQuery.refetch();
    } catch (err) {
      const message = friendlyError(err);
      if (message.toLowerCase().includes("already") || message.toLowerCase().includes("duplicate")) {
        setWatchOverrides((current) => ({ ...current, [item.job_id]: "watching" }));
        setReviewMessage("Company is already on your watchlist.");
        return;
      }
      setReviewError(message);
    }
  }

  function markOpenedWorkspace(item: DailyScoutReviewItem) {
    setReviewState((current) => upsertDailyScoutReviewState(current, item.job_id, "opened_workspace"));
  }

  async function copyJobUrl(item: DailyScoutReviewItem) {
    const url = item.apply_url ?? item.job_url;
    if (!url) {
      setReviewError("This job does not include a job URL.");
      return;
    }
    setReviewError(null);
    try {
      await navigator.clipboard.writeText(url);
      setReviewMessage("Job URL copied.");
    } catch {
      setReviewError("Could not copy job URL. You can open the job and copy it manually.");
    }
  }

  async function bulkReviewDecision(
    items: DailyScoutReviewItem[],
    status: JobDecisionStatus,
    reviewStatus: DailyScoutReviewStatus,
  ) {
    for (const item of items) {
      await applyReviewDecision(item, status, reviewStatus);
    }
  }

  async function rankItemsWithResume(items: DailyScoutReviewItem[], limit = 10) {
    if (resumeRankLoading) return;
    setResumeRankError(null);
    setResumeRankMessage(null);

    const activeResume = activeResumeQuery.data ?? await activeResumeQuery.refetch().then((response) => response.data ?? null);
    if (!activeResume) {
      setResumeRankMessage("No active resume found. Upload or activate a resume to rank jobs by resume fit.");
      return;
    }
    if (activeResume.parse_status === "failed") {
      setResumeRankError("Active resume parsing failed. Reparse or upload another resume before ranking.");
      return;
    }

    const targetItems = items
      .filter((item) => item.job_id)
      .filter((item) => !resumeFitOverrides[item.job_id])
      .slice(0, limit);
    if (!targetItems.length) {
      setResumeRankMessage("Visible jobs already have resume ranking for this session.");
      return;
    }

    setResumeRankLoading(true);
    let analyzed = 0;
    let failed = 0;
    let cache = resumeFitCache;

    for (const item of targetItems) {
      const cached = cache.find((entry) => entry.job_id === item.job_id && entry.resume_id === activeResume.id);
      if (cached) {
        setResumeFitOverrides((current) => ({ ...current, [item.job_id]: cacheEntryToReviewFields(cached) }));
        analyzed += 1;
        continue;
      }

      setResumeFitOverrides((current) => ({
        ...current,
        [item.job_id]: {
          resume_fit_score: null,
          resume_fit_tier: "unknown",
          resume_fit_summary: null,
          resume_strengths: [],
          resume_gaps: [],
          resume_bullet_sources: [],
          resume_action: "needs_review",
          resume_analysis_status: "loading",
        },
      }));

      try {
        const packet = await generateApplicationPacketForJob(item.job_id, {
          update_decision: false,
          include_resume_bullets: true,
          include_cover_note_outline: false,
          include_cold_dm_outline: false,
          include_checklist: true,
          include_risk_review: true,
        });
        let improvement = null;
        try {
          improvement = await generateResumeImprovementForJob(item.job_id, {
            update_decision: false,
            include_section_suggestions: true,
            include_bullet_suggestions: true,
            include_skill_gap_suggestions: true,
            include_project_reordering: true,
            include_remote_fit_suggestions: true,
          });
        } catch {
          improvement = null;
        }
        const fit = deriveResumeFitFromPacket(packet, improvement, item);
        setResumeFitOverrides((current) => ({ ...current, [item.job_id]: fit }));
        cache = upsertResumeFitCache(cache, item.job_id, activeResume.id, fit);
        setResumeFitCache(cache);
        analyzed += 1;
      } catch (err) {
        failed += 1;
        setResumeFitOverrides((current) => ({
          ...current,
          [item.job_id]: {
            resume_fit_score: null,
            resume_fit_tier: "unknown",
            resume_fit_summary: null,
            resume_strengths: [],
            resume_gaps: [],
            resume_bullet_sources: [],
            resume_action: "needs_review",
            resume_analysis_status: "failed",
            resume_analysis_error: friendlyError(err),
          },
        }));
      }
    }

    setResumeRankLoading(false);
    setResumeRankMessage(`${analyzed} of ${targetItems.length} jobs analyzed.${failed ? ` ${failed} failed.` : ""}`);
  }

  function analyzeAllVisible(items: DailyScoutReviewItem[]) {
    if (items.length > 20 && !window.confirm(`Analyze ${items.length} visible jobs with your resume? This can take a while.`)) {
      return;
    }
    void rankItemsWithResume(items, items.length);
  }

  const topRecommendations = result?.top_recommendations ?? [];
  const sourceResults = result?.source_results ?? [];
  const recentRuns = runsQuery.data?.items ?? [];
  const selectedRuns = recentRuns.filter((run) => {
    const id = stringValue(run.id) ?? stringValue(run.discovery_run_id);
    return Boolean(id && selectedRunIds.includes(id));
  });
  const effectivenessSummary = buildSourceEffectivenessSummary([
    ...recentRuns,
    ...sourceResults,
  ]);
  const sourceAdvisor = buildSourceQualityAdvisor({
    runs: recentRuns,
    sourceResults,
    availableSources,
    ashbyBoardSlugs: parseBoardSlugs(options.ashby.board_slugs_text),
  });
  const dailyPayload = buildDailyScoutPayload({
    advisors: sourceAdvisor,
    options,
    availableSources,
    includeWeeklyManualSources,
  });
  const reviewQueue = buildDailyScoutReviewQueue(
    dailyResult,
    [
      ...(decisionsQuery.data?.items ?? []),
      ...Object.values(decisionOverrides),
    ],
    watchlistQuery.data?.items ?? [],
    fallbackMatchesQuery.data?.items ?? [],
    reviewState,
    includeSkippedReviewItems,
  ).map((item) => ({
    ...item,
    ...(resumeFitOverrides[item.job_id] ?? {}),
    company_watch_status: watchOverrides[item.job_id] ?? item.company_watch_status,
    review_status:
      watchOverrides[item.job_id] && item.review_status === "unreviewed"
        ? "watched_company"
        : item.review_status,
  }));
  const selectedRunSources = result?.recommendation_source_filter ?? selectedSources;
  const sourceScoped = Boolean(
    result?.recommendation_scope === "run_jobs" ||
      result?.recommendation_scope === "source_platform",
  );

  return (
    <>
      <PageHeader
        title="Discovery Control Center"
        description="Run startup/job sources and inspect what was fetched, enriched, ingested, scored, rejected, or skipped."
        actions={
          <div className="flex flex-wrap gap-2">
            <Link href="/recommendations" className="rounded border border-[#c8ced8] bg-white px-3 py-2 text-sm font-medium text-[#344054] hover:bg-[#f8fafc]">
              Recommended Jobs
            </Link>
            <Link href="/jobs/pipeline" className="rounded border border-[#c8ced8] bg-white px-3 py-2 text-sm font-medium text-[#344054] hover:bg-[#f8fafc]">
              Pipeline
            </Link>
            <Link href="/applications/follow-ups" className="rounded border border-[#c8ced8] bg-white px-3 py-2 text-sm font-medium text-[#344054] hover:bg-[#f8fafc]">
              Follow-ups
            </Link>
          </div>
        }
      />

      {planQuery.error ? (
        <Notice tone="warning">
          Discovery plan unavailable. The backend may be offline, but you can still prepare a run payload.
        </Notice>
      ) : null}

      <DailyScoutPanel
        payloadResult={dailyPayload}
        advisors={sourceAdvisor}
        includeWeeklyManualSources={includeWeeklyManualSources}
        running={running || dailyRunning}
        phaseText={dailyRunning ? dailyScoutPhases[dailyPhaseIndex] : null}
        onIncludeWeeklyManualSourcesChange={setIncludeWeeklyManualSources}
        onRunDailyScout={() => void runDailyScout()}
        onPreviewPayload={() => {
          setCopyMessage(null);
          setPayloadCopied(false);
          setShowPayloadPreview(true);
        }}
        onSelectAdvisorDaily={() => setSelectedSources(dailyPayload.selectedSources)}
        onSelectSafeDefaults={() =>
          setSelectedSources(safeDefaultDailySources.filter((source) => availableSources.includes(source)))
        }
        onSelectAllAvailable={() => setSelectedSources(availableSources)}
        onRunManualSelection={runSelected}
      />

      <DiscoveryRunPresets
        presets={presets}
        advisors={sourceAdvisor}
        options={options}
        selectedSources={selectedSources}
        sessionRuns={presetSessionRuns}
        running={running}
        message={presetMessage}
        onRunPreset={(preset) => void runPreset(preset)}
        onApplyPreset={applyPreset}
        onSaveCurrentPreset={saveCurrentPreset}
        onUpdatePreset={updatePreset}
        onDuplicatePreset={duplicatePreset}
        onDeletePreset={deletePreset}
      />

      <div className="mb-5 grid gap-5 xl:grid-cols-[minmax(0,1fr)_360px]">
        <div className="space-y-5">
          <DiscoverySourceSelector
            sources={availableSources}
            selected={selectedSources}
            options={options}
            onToggle={toggleSource}
            onOptionsChange={setOptions}
          />

          <RunControls
            force={force}
            scoreAfterIngestion={scoreAfterIngestion}
            running={running}
            disabled={!selectedSources.length}
            onForceChange={setForce}
            onScoreAfterIngestionChange={setScoreAfterIngestion}
            onRunSelected={runSelected}
            onRunRemote={() => runPayload(buildPayload(defaultSelected, options, true, true))}
            onRunHackerNews={() => runPayload(buildPayload(["hacker_news"], options, true, true))}
            onRunYc={() => runPayload(buildPayload(["ycombinator"], options, true, true))}
            onRunAshby={() => runPayload(buildPayload(["ashby"], options, true, true))}
          />
        </div>

        <DiscoveryRunHistory
          loading={runsQuery.isLoading}
          error={Boolean(runsQuery.error)}
          runs={recentRuns}
          selectedRunIds={selectedRunIds}
          compareActive={compareOpen}
          compareMessage={compareMessage}
          running={running}
          rerunMessage={rerunMessage}
          onRefresh={() => runsQuery.refetch()}
          onOpenDetails={openRunDetails}
          onToggleCompare={toggleCompareRun}
          onCompare={compareRuns}
          onRerunSource={rerunSource}
        />
      </div>

      {error ? <Notice tone="danger">{error}</Notice> : null}

      <div className="mb-5">
        <SourceQualityAdvisor
          advisors={sourceAdvisor}
          onSelectSources={(sources) => {
            setSelectedSources(sources);
            setCompareMessage(null);
          }}
        />
      </div>

      {!result && !running && !error ? (
        <div className="rounded-md border border-[#d9dee8] bg-white p-5 text-sm text-[#667085]">
          Choose sources and run discovery to see what ScoutAI finds.
        </div>
      ) : null}

      {running ? (
        <div className="rounded-md border border-[#bfdbfe] bg-[#eff6ff] p-5 text-sm font-medium text-[#1d4ed8]">
          Running discovery. Duplicate submissions are disabled until this completes.
        </div>
      ) : null}

      {result ? (
        <div className="space-y-5">
          {dailyResult ? (
            <>
              <DailyScoutRunResult
                result={dailyResult}
                recentRunsCount={recentRuns.length}
                onOpenSourceDetails={openRunDetails}
              />
              <DailyScoutReviewQueue
                items={reviewQueue}
                loading={decisionsQuery.isLoading || watchlistQuery.isLoading || fallbackMatchesQuery.isLoading}
                message={reviewMessage}
                error={reviewError}
                includeSkipped={includeSkippedReviewItems}
                onIncludeSkippedChange={setIncludeSkippedReviewItems}
                onDecisionAction={(item, status, reviewStatus) =>
                  void applyReviewDecision(item, status, reviewStatus)
                }
                onWatchCompany={(item) => void watchCompany(item)}
                onOpenedWorkspace={markOpenedWorkspace}
                onCopyJobUrl={(item) => void copyJobUrl(item)}
                onBulkDecisionAction={(items, status, reviewStatus) =>
                  void bulkReviewDecision(items, status, reviewStatus)
                }
                onRunDailyScoutAgain={() => void runDailyScout()}
                onTryRemoteJobsPreset={() => {
                  const preset = presets.find((item) => item.id === "remote-jobs-only");
                  if (preset) void runPreset(preset);
                }}
                onTryHnPreset={() => {
                  const preset = presets.find((item) => item.id === "hn-startup-signals");
                  if (preset) void runPreset(preset);
                }}
                activeResume={activeResumeQuery.data}
                activeResumeLoading={activeResumeQuery.isLoading}
                resumeRankLoading={resumeRankLoading}
                resumeRankMessage={resumeRankMessage}
                resumeRankError={resumeRankError}
                onRankWithResume={(items) => void rankItemsWithResume(items, 10)}
                onAnalyzeNext={(items) => void rankItemsWithResume(items, 10)}
                onAnalyzeAllVisible={analyzeAllVisible}
                onActionCenterDecisionUpdated={(item, decision) => {
                  const status = decision.decision_status ?? decision.status ?? "saved";
                  setDecisionOverrides((current) => ({ ...current, [item.job_id]: decision }));
                  setReviewState((current) =>
                    upsertDailyScoutReviewState(current, item.job_id, reviewStatusFromDecisionStatus(status)),
                  );
                  setReviewMessage(`${item.title} marked as ${statusLabel(status)}.`);
                }}
                onActionCenterWatchUpdated={(item) => {
                  setWatchOverrides((current) => ({ ...current, [item.job_id]: "watching" }));
                  setReviewState((current) => upsertDailyScoutReviewState(current, item.job_id, "watched_company"));
                  setReviewMessage(item.company_name ? `${item.company_name} added to watchlist.` : "Company added to watchlist.");
                }}
                onActionCenterResumeFitUpdated={(item, result) => {
                  setResumeFitOverrides((current) => ({ ...current, [item.job_id]: result }));
                  const resumeId = activeResumeQuery.data?.id;
                  if (resumeId) {
                    setResumeFitCache((current) => upsertResumeFitCache(current, item.job_id, resumeId, result));
                  }
                }}
              />
              <DailyScoutNextActions
                onCompareRuns={() => setCompareOpen(true)}
                onRunManualSources={runSelected}
              />
            </>
          ) : null}

          <DiscoveryRunSummary result={result} />
          <WarningsPanel warnings={result.warnings ?? []} />
          <DiscoverySourceEffectiveness summary={effectivenessSummary} />

          {compareOpen ? (
            <DiscoveryRunComparison
              runs={selectedRuns}
              onClear={() => {
                setCompareOpen(false);
                setSelectedRunIds([]);
                setCompareMessage(null);
              }}
            />
          ) : null}

          <section className="space-y-4">
            <h2 className="text-base font-semibold text-[#171923]">Source Diagnostics</h2>
            {sourceResults.length ? (
              sourceResults.map((source, index) => (
                <DiscoverySourceResultCard
                  key={`${source.source ?? "source"}-${index}`}
                  result={source}
                  onOpenDetails={openRunDetails}
                />
              ))
            ) : (
              <div className="rounded-md border border-[#d9dee8] bg-white p-5 text-sm text-[#667085]">
                No source-level diagnostics returned.
              </div>
            )}
          </section>

          <DiscoveryTopRecommendations
            recommendations={topRecommendations}
            selectedSources={selectedRunSources}
            sourceScoped={sourceScoped}
          />

          <details className="rounded-md border border-[#d9dee8] bg-white p-5">
            <summary className="cursor-pointer text-sm font-semibold text-[#344054]">
              Show raw JSON
            </summary>
            <pre className="mt-4 max-h-96 overflow-auto rounded bg-[#101828] p-4 text-xs leading-5 text-white">
              {JSON.stringify(result, null, 2)}
            </pre>
          </details>
        </div>
      ) : null}

      {!result && compareOpen ? (
        <div className="space-y-5">
          <DiscoverySourceEffectiveness summary={effectivenessSummary} />
          <DiscoveryRunComparison
            runs={selectedRuns}
            onClear={() => {
              setCompareOpen(false);
              setSelectedRunIds([]);
              setCompareMessage(null);
            }}
          />
        </div>
      ) : null}

      <DiscoveryRunDetailDrawer
        run={detailsRun}
        loadingRunId={detailsRunId}
        error={detailsError}
        onClose={closeRunDetails}
      />

      {showPayloadPreview ? (
        <PayloadPreviewDrawer
          payload={dailyPayload.payload}
          error={copyMessage}
          copied={payloadCopied}
          onCopy={() => void copyPayload()}
          onRun={() => {
            setShowPayloadPreview(false);
            void runDailyScout();
          }}
          onClose={() => setShowPayloadPreview(false)}
        />
      ) : null}
    </>
  );
}

function RunControls({
  force,
  scoreAfterIngestion,
  running,
  disabled,
  onForceChange,
  onScoreAfterIngestionChange,
  onRunSelected,
  onRunRemote,
  onRunHackerNews,
  onRunYc,
  onRunAshby,
}: {
  force: boolean;
  scoreAfterIngestion: boolean;
  running: boolean;
  disabled: boolean;
  onForceChange: (value: boolean) => void;
  onScoreAfterIngestionChange: (value: boolean) => void;
  onRunSelected: () => void;
  onRunRemote: () => void;
  onRunHackerNews: () => void;
  onRunYc: () => void;
  onRunAshby: () => void;
}) {
  return (
    <section className="rounded-md border border-[#d9dee8] bg-white p-5">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
        <div className="flex flex-wrap gap-3">
          <label className="flex items-center gap-2 text-sm text-[#344054]">
            <input type="checkbox" checked={force} onChange={(event) => onForceChange(event.target.checked)} className="h-4 w-4 accent-[#172033]" />
            Force run
          </label>
          <label className="flex items-center gap-2 text-sm text-[#344054]">
            <input type="checkbox" checked={scoreAfterIngestion} onChange={(event) => onScoreAfterIngestionChange(event.target.checked)} className="h-4 w-4 accent-[#172033]" />
            Score after ingestion
          </label>
        </div>
        <button
          type="button"
          onClick={onRunSelected}
          disabled={disabled || running}
          className="rounded bg-[#172033] px-4 py-2 text-sm font-medium text-white hover:bg-[#0f1728] disabled:cursor-not-allowed disabled:opacity-60"
        >
          {running ? "Running..." : "Run Discovery"}
        </button>
      </div>
      <div className="mt-4 flex flex-wrap gap-2">
        <QuickButton disabled={running} onClick={onRunRemote}>Run Remote Job Sources</QuickButton>
        <QuickButton disabled={running} onClick={onRunHackerNews}>Run Hacker News Only</QuickButton>
        <QuickButton disabled={running} onClick={onRunYc}>Run YC Only</QuickButton>
        <QuickButton disabled={running} onClick={onRunAshby}>Run Ashby Boards</QuickButton>
      </div>
    </section>
  );
}

function QuickButton({
  children,
  disabled,
  onClick,
}: {
  children: ReactNode;
  disabled: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      disabled={disabled}
      onClick={onClick}
      className="rounded border border-[#c8ced8] bg-white px-3 py-2 text-sm font-medium text-[#344054] hover:bg-[#f8fafc] disabled:cursor-not-allowed disabled:opacity-60"
    >
      {children}
    </button>
  );
}

function WarningsPanel({ warnings }: { warnings: string[] }) {
  if (!warnings.length) return null;
  return (
    <div className="rounded-md border border-[#fedf89] bg-[#fffbeb] p-4 text-sm text-[#92400e]">
      <p className="font-semibold">Warnings</p>
      <ul className="mt-2 list-disc space-y-1 pl-5">
        {warnings.map((warning, index) => (
          <li key={`${warning}-${index}`}>{warning}</li>
        ))}
      </ul>
    </div>
  );
}

function Notice({ tone, children }: { tone: "warning" | "danger"; children: ReactNode }) {
  const classes =
    tone === "danger"
      ? "border-[#fecaca] bg-[#fff7f7] text-[#991b1b]"
      : "border-[#fedf89] bg-[#fffbeb] text-[#92400e]";
  return <div className={`mb-5 rounded-md border p-4 text-sm ${classes}`}>{children}</div>;
}

function buildPayload(
  sources: string[],
  options: DiscoveryOptionsState,
  force: boolean,
  scoreAfterIngestion: boolean,
): RemoteJobDiscoveryRunRequest {
  const payload: RemoteJobDiscoveryRunRequest = {
    force,
    sources,
    score_after_ingestion: scoreAfterIngestion,
  };
  if (sources.includes("himalayas")) payload.himalayas = options.himalayas;
  if (sources.includes("we_work_remotely")) payload.we_work_remotely = options.we_work_remotely;
  if (sources.includes("remotive")) payload.remotive = options.remotive;
  if (sources.includes("hacker_news")) payload.hacker_news = { ...options.hacker_news, enabled: true };
  if (sources.includes("ycombinator")) payload.ycombinator = { ...options.ycombinator, enabled: true };
  if (sources.includes("ashby")) {
    const { board_slugs_text: _boardSlugsText, ...ashbyOptions } = options.ashby;
    payload.ashby = {
      ...ashbyOptions,
      enabled: true,
      board_slugs: parseBoardSlugs(options.ashby.board_slugs_text),
    };
  }
  return payload;
}

function buildRerunPayload(
  source: string,
  run: DiscoveryRunListItem,
  options: DiscoveryOptionsState,
): RemoteJobDiscoveryRunRequest | null {
  if (source === "hacker_news") {
    return {
      force: true,
      sources: ["hacker_news"],
      score_after_ingestion: true,
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
        enabled: true,
      },
    };
  }

  if (source === "ashby") {
    const boardSlugs = boardSlugsFromRun(run);
    if (!boardSlugs.length) return null;
    return {
      force: true,
      sources: ["ashby"],
      score_after_ingestion: true,
      ashby: {
        ...options.ashby,
        enabled: true,
        board_slugs: boardSlugs,
      },
    };
  }

  if (["himalayas", "we_work_remotely", "remotive", "ycombinator"].includes(source)) {
    return buildPayload([source], options, true, true);
  }

  return {
    force: true,
    sources: [source],
    score_after_ingestion: true,
  };
}

function detailRunId(run: Record<string, unknown>) {
  return stringValue(run.id) ?? stringValue(run.discovery_run_id);
}

function boardSlugsFromRun(run: DiscoveryRunListItem) {
  const containers = [
    run.metadata,
    run.metadata_json,
    objectValue(run.request),
    objectValue(run.request_payload),
    objectValue(run.payload),
  ];

  for (const container of containers) {
    const direct = stringArrayValue(container?.board_slugs);
    if (direct.length) return direct;
    const ashby = objectValue(container?.ashby);
    const nested = stringArrayValue(ashby?.board_slugs);
    if (nested.length) return nested;
  }

  return [];
}

function parseBoardSlugs(value?: string) {
  return (value ?? "")
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

function friendlyError(error: unknown) {
  if (error instanceof Error) return error.message;
  return "Discovery request failed. Check the backend API and try again.";
}

function statusLabel(value: string) {
  return value.replace(/_/g, " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function remoteInterest(value?: string | null) {
  if (value === "work_from_anywhere" || value === "remote_global_unspecified") return "remote_worldwide";
  if (value === "remote_india_eligible") return "remote_india";
  if (value === "hybrid") return "hybrid_possible";
  return "unknown";
}

function juniorSignal(title?: string | null, reason?: string | null) {
  const text = `${title ?? ""} ${reason ?? ""}`.toLowerCase();
  if (/\b(internship|intern|entry[- ]level|junior|new grad|graduate|associate)\b/.test(text)) {
    return "moderate";
  }
  return "unknown";
}

function stringValue(value: unknown) {
  return typeof value === "string" && value.trim() ? value : null;
}

function objectValue(value: unknown) {
  return value && typeof value === "object" && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : null;
}

function stringArrayValue(value: unknown) {
  return Array.isArray(value)
    ? value.filter((item): item is string => typeof item === "string" && Boolean(item.trim()))
    : [];
}
