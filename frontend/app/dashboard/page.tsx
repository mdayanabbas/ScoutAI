"use client";

import { RecentActivity } from "@/components/dashboard/RecentActivity";
import { SummaryCards } from "@/components/dashboard/SummaryCards";
import { PageHeader } from "@/components/layout/PageHeader";
import { useDashboard } from "@/hooks/use-dashboard";

function LoadingState() {
  return (
    <div className="space-y-6">
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {Array.from({ length: 8 }).map((_, index) => (
          <div
            key={index}
            className="h-32 animate-pulse rounded-md border border-[#d9dee8] bg-white"
          />
        ))}
      </div>
      <div className="h-72 animate-pulse rounded-md border border-[#d9dee8] bg-white" />
    </div>
  );
}

export default function DashboardPage() {
  const { data, isLoading, isError, error, refetch } = useDashboard();

  return (
    <>
      <PageHeader
        title="Dashboard"
        description="A compact view of ScoutAI's company, job, crawl, and agent activity."
      />

      {isLoading ? <LoadingState /> : null}

      {isError ? (
        <div className="rounded-md border border-[#fecaca] bg-[#fff7f7] p-4">
          <h2 className="text-sm font-semibold text-[#991b1b]">
            Dashboard could not load
          </h2>
          <p className="mt-1 text-sm text-[#7f1d1d]">
            {error instanceof Error ? error.message : "Check the backend API."}
          </p>
          <button
            type="button"
            onClick={() => refetch()}
            className="mt-4 rounded bg-[#172033] px-3 py-2 text-sm font-medium text-white"
          >
            Retry
          </button>
        </div>
      ) : null}

      {data ? (
        <div className="space-y-6">
          <SummaryCards summary={data.summary} />
          <RecentActivity items={data.recent_activity} />
        </div>
      ) : null}
    </>
  );
}
