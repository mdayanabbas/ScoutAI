"use client";

import type { ReactNode } from "react";

import type {
  AshbyRemoteDiscoveryOptions,
  DiscoverySource,
  HackerNewsRemoteDiscoveryOptions,
  HimalayasRemoteDiscoveryOptions,
  RemotiveRemoteDiscoveryOptions,
  WWRRemoteDiscoveryOptions,
  YCombinatorRemoteDiscoveryOptions,
} from "@/types/discovery";

export const sourceLabels: Record<string, string> = {
  himalayas: "Himalayas",
  we_work_remotely: "We Work Remotely",
  remotive: "Remotive",
  hacker_news: "Hacker News",
  ycombinator: "Y Combinator",
  ashby: "Ashby",
};

export const sourceHelp: Record<string, string> = {
  himalayas: "Targeted remote job source for startup-friendly engineering roles.",
  we_work_remotely: "RSS source for practical remote software jobs.",
  remotive: "Remote jobs API source with broad role coverage.",
  hacker_news: "Candidate-first source. Best for YC/startup hiring signals. Needs enrichment before scoring.",
  ycombinator: "Startup job-board source/enricher.",
  ashby: "Job-board resolver/enricher. Useful for board slugs like supabase, artie, charge-robotics.",
};

export type DiscoveryOptionsState = {
  himalayas: HimalayasRemoteDiscoveryOptions;
  we_work_remotely: WWRRemoteDiscoveryOptions;
  remotive: RemotiveRemoteDiscoveryOptions;
  hacker_news: HackerNewsRemoteDiscoveryOptions;
  ycombinator: YCombinatorRemoteDiscoveryOptions;
  ashby: AshbyRemoteDiscoveryOptions & { board_slugs_text?: string };
};

type Props = {
  sources: DiscoverySource[];
  selected: string[];
  options: DiscoveryOptionsState;
  onToggle: (source: string) => void;
  onOptionsChange: (options: DiscoveryOptionsState) => void;
};

export function DiscoverySourceSelector({
  sources,
  selected,
  options,
  onToggle,
  onOptionsChange,
}: Props) {
  return (
    <section className="rounded-md border border-[#d9dee8] bg-white p-5">
      <div className="mb-4">
        <h2 className="text-base font-semibold text-[#171923]">Sources</h2>
        <p className="mt-1 text-sm text-[#667085]">
          Pick one or more discovery sources, then adjust only the options you need.
        </p>
      </div>

      <div className="grid gap-3 lg:grid-cols-3">
        {sources.map((source) => {
          const checked = selected.includes(source);
          return (
            <label
              key={source}
              className={[
                "block rounded-md border p-4 transition-colors",
                checked
                  ? "border-[#172033] bg-[#f8fafc]"
                  : "border-[#d9dee8] bg-white hover:bg-[#f8fafc]",
              ].join(" ")}
            >
              <span className="flex items-start gap-3">
                <input
                  type="checkbox"
                  checked={checked}
                  onChange={() => onToggle(source)}
                  className="mt-1 h-4 w-4 accent-[#172033]"
                />
                <span>
                  <span className="block text-sm font-semibold text-[#171923]">
                    {sourceLabels[source] ?? source}
                  </span>
                  <span className="mt-1 block text-xs leading-5 text-[#667085]">
                    {sourceHelp[source] ?? "Discovery source."}
                  </span>
                </span>
              </span>
            </label>
          );
        })}
      </div>

      <div className="mt-4 space-y-3">
        {selected.map((source) => (
          <details key={source} className="rounded-md border border-[#e4e7ec] bg-[#fcfcfd] p-4">
            <summary className="cursor-pointer text-sm font-semibold text-[#344054]">
              {sourceLabels[source] ?? source} options
            </summary>
            <SourceOptions
              source={source}
              options={options}
              onOptionsChange={onOptionsChange}
            />
          </details>
        ))}
      </div>
    </section>
  );
}

function SourceOptions({
  source,
  options,
  onOptionsChange,
}: {
  source: string;
  options: DiscoveryOptionsState;
  onOptionsChange: (options: DiscoveryOptionsState) => void;
}) {
  const update = <K extends keyof DiscoveryOptionsState>(
    key: K,
    value: DiscoveryOptionsState[K],
  ) => onOptionsChange({ ...options, [key]: value });

  if (source === "hacker_news") {
    const hn = options.hacker_news;
    return (
      <div className="mt-4 grid gap-3 md:grid-cols-3">
        <Field label="Feeds">
          <select
            multiple
            value={hn.feeds ?? ["jobs"]}
            onChange={(event) =>
              update("hacker_news", {
                ...hn,
                feeds: Array.from(event.currentTarget.selectedOptions).map((item) => item.value),
              })
            }
            className="h-20 w-full rounded border border-[#c8ced8] bg-white px-3 py-2 text-sm"
          >
            <option value="jobs">jobs</option>
            <option value="show">show</option>
          </select>
        </Field>
        <NumberField label="Limit" value={hn.limit ?? 100} onChange={(limit) => update("hacker_news", { ...hn, limit })} />
        <NumberField label="Lookback Days" value={hn.lookback_days ?? 30} onChange={(lookback_days) => update("hacker_news", { ...hn, lookback_days })} />
        <NumberField label="Minimum Score" value={hn.minimum_score ?? 0} onChange={(minimum_score) => update("hacker_news", { ...hn, minimum_score })} />
        <Toggle label="Include no website" checked={hn.include_items_without_website ?? true} onChange={(include_items_without_website) => update("hacker_news", { ...hn, include_items_without_website })} />
        <Toggle label="Enrich domains" checked={hn.enrich_domains ?? true} onChange={(enrich_domains) => update("hacker_news", { ...hn, enrich_domains })} />
        <Toggle label="Ingest jobs" checked={hn.ingest_jobs ?? true} onChange={(ingest_jobs) => update("hacker_news", { ...hn, ingest_jobs })} />
        <Toggle label="Enrich jobs" checked={hn.enrich_jobs ?? true} onChange={(enrich_jobs) => update("hacker_news", { ...hn, enrich_jobs })} />
        <Toggle label="Score jobs" checked={hn.score_jobs ?? true} onChange={(score_jobs) => update("hacker_news", { ...hn, score_jobs })} />
      </div>
    );
  }

  if (source === "ycombinator") {
    const yc = options.ycombinator;
    return (
      <div className="mt-4 grid gap-3 md:grid-cols-3">
        <NumberField label="Max Pages" value={yc.max_pages ?? 5} onChange={(max_pages) => update("ycombinator", { ...yc, max_pages })} />
        <Toggle label="Remote only" checked={yc.remote_only ?? false} onChange={(remote_only) => update("ycombinator", { ...yc, remote_only })} />
        <Toggle label="Recent only" checked={yc.include_recent_only ?? true} onChange={(include_recent_only) => update("ycombinator", { ...yc, include_recent_only })} />
        <NumberField label="Lookback Days" value={yc.lookback_days ?? 60} onChange={(lookback_days) => update("ycombinator", { ...yc, lookback_days })} />
        <Toggle label="Ingest jobs" checked={yc.ingest_jobs ?? true} onChange={(ingest_jobs) => update("ycombinator", { ...yc, ingest_jobs })} />
        <Toggle label="Enrich jobs" checked={yc.enrich_jobs ?? true} onChange={(enrich_jobs) => update("ycombinator", { ...yc, enrich_jobs })} />
        <Toggle label="Score jobs" checked={yc.score_jobs ?? true} onChange={(score_jobs) => update("ycombinator", { ...yc, score_jobs })} />
      </div>
    );
  }

  if (source === "ashby") {
    const ashby = options.ashby;
    return (
      <div className="mt-4 grid gap-3 md:grid-cols-3">
        <Field label="Board slugs">
          <input
            value={ashby.board_slugs_text ?? ""}
            onChange={(event) =>
              update("ashby", { ...ashby, board_slugs_text: event.target.value })
            }
            placeholder="supabase, artie, charge-robotics"
            className="w-full rounded border border-[#c8ced8] px-3 py-2 text-sm"
          />
        </Field>
        <NumberField label="Max jobs per board" value={ashby.max_jobs_per_board ?? 50} onChange={(max_jobs_per_board) => update("ashby", { ...ashby, max_jobs_per_board })} />
        <Toggle label="Enrich jobs" checked={ashby.enrich_jobs ?? true} onChange={(enrich_jobs) => update("ashby", { ...ashby, enrich_jobs })} />
        <Toggle label="Score jobs" checked={ashby.score_jobs ?? true} onChange={(score_jobs) => update("ashby", { ...ashby, score_jobs })} />
      </div>
    );
  }

  if (source === "himalayas") {
    const h = options.himalayas;
    return (
      <div className="mt-4 grid gap-3 md:grid-cols-3">
        <NumberField label="Max queries" value={h.max_queries ?? 10} onChange={(max_queries) => update("himalayas", { ...h, max_queries })} />
        <NumberField label="Max pages per query" value={h.max_pages_per_query ?? 2} onChange={(max_pages_per_query) => update("himalayas", { ...h, max_pages_per_query })} />
      </div>
    );
  }

  if (source === "we_work_remotely") {
    const wwr = options.we_work_remotely;
    return (
      <div className="mt-4 grid gap-3 md:grid-cols-3">
        <Toggle label="Include all other" checked={wwr.include_all_other ?? true} onChange={(include_all_other) => update("we_work_remotely", { ...wwr, include_all_other })} />
        <NumberField label="Max items per feed" value={wwr.max_items_per_feed ?? 150} onChange={(max_items_per_feed) => update("we_work_remotely", { ...wwr, max_items_per_feed })} />
      </div>
    );
  }

  const remotive = options.remotive;
  return (
    <div className="mt-4 grid gap-3 md:grid-cols-3">
      <NumberField label="Max requests" value={remotive.max_requests ?? 4} onChange={(max_requests) => update("remotive", { ...remotive, max_requests })} />
      <NumberField label="Limit per request" value={remotive.limit_per_request ?? 200} onChange={(limit_per_request) => update("remotive", { ...remotive, limit_per_request })} />
    </div>
  );
}

function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <label className="block text-xs font-medium text-[#475467]">
      <span className="mb-1 block">{label}</span>
      {children}
    </label>
  );
}

function NumberField({
  label,
  value,
  onChange,
}: {
  label: string;
  value: number;
  onChange: (value: number) => void;
}) {
  return (
    <Field label={label}>
      <input
        type="number"
        min={0}
        value={value}
        onChange={(event) => onChange(Number(event.target.value))}
        className="w-full rounded border border-[#c8ced8] px-3 py-2 text-sm"
      />
    </Field>
  );
}

function Toggle({
  label,
  checked,
  onChange,
}: {
  label: string;
  checked: boolean;
  onChange: (checked: boolean) => void;
}) {
  return (
    <label className="flex min-h-10 items-center gap-2 rounded border border-[#e4e7ec] bg-white px-3 py-2 text-sm text-[#344054]">
      <input
        type="checkbox"
        checked={checked}
        onChange={(event) => onChange(event.target.checked)}
        className="h-4 w-4 accent-[#172033]"
      />
      {label}
    </label>
  );
}
