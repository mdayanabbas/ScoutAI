import type { DashboardSummary } from "@/types/dashboard";

const metrics: Array<{
  label: string;
  key: keyof DashboardSummary;
  helper: string;
}> = [
  { label: "Total Companies", key: "total_companies", helper: "Tracked targets" },
  { label: "Total Jobs", key: "total_jobs", helper: "Known openings" },
  { label: "Active Jobs", key: "active_jobs", helper: "Currently open" },
  { label: "Remote Jobs", key: "remote_jobs", helper: "Remote-friendly" },
  {
    label: "Companies Added Today",
    key: "companies_added_today",
    helper: "New records",
  },
  { label: "Jobs Added Today", key: "jobs_added_today", helper: "Fresh roles" },
  { label: "Crawl Runs", key: "recent_crawl_runs", helper: "Last 7 days" },
  { label: "Agent Runs", key: "recent_agent_runs", helper: "Last 7 days" },
];

export function SummaryCards({ summary }: { summary: DashboardSummary }) {
  return (
    <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
      {metrics.map((metric) => (
        <article
          key={metric.key}
          className="rounded-md border border-[#d9dee8] bg-white p-4 shadow-sm"
        >
          <p className="text-sm font-medium text-[#667085]">{metric.label}</p>
          <div className="mt-3 flex items-end justify-between gap-3">
            <p className="text-3xl font-semibold tracking-normal text-[#171923]">
              {summary[metric.key].toLocaleString()}
            </p>
            <p className="pb-1 text-xs text-[#667085]">{metric.helper}</p>
          </div>
        </article>
      ))}
    </section>
  );
}
