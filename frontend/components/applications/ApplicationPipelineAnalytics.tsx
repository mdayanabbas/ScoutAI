"use client";

import Link from "next/link";
import type { ReactNode } from "react";

import { decisionStatusLabel } from "@/components/recommendations/RecommendedJobCard";
import { formatMatchTier, labelize } from "@/components/recommendations/recommendation-format";
import type { ApplicationPipelineAnalytics as Analytics } from "@/lib/application-pipeline-analytics";

export function ApplicationPipelineAnalytics({
  analytics,
  label = "Based on loaded tracked jobs.",
}: {
  analytics: Analytics;
  label?: string;
}) {
  if (analytics.total_tracked === 0) {
    return (
      <section className="mb-5 rounded-md border border-dashed border-[#c8ced8] bg-white p-6 text-center">
        <h2 className="text-base font-semibold text-[#171923]">No tracked jobs yet.</h2>
        <p className="mt-2 text-sm text-[#667085]">Analytics will appear once you save jobs.</p>
        <Link
          href="/recommendations"
          className="mt-4 inline-block rounded bg-[#172033] px-3 py-2 text-sm font-medium text-white"
        >
          Go to Recommended Jobs
        </Link>
      </section>
    );
  }

  return (
    <section id="pipeline-analytics" className="mb-5 space-y-4">
      <div className="flex flex-col gap-1">
        <h2 className="text-lg font-semibold text-[#171923]">Pipeline Analytics</h2>
        <p className="text-sm text-[#667085]">{label}</p>
      </div>

      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-6">
        <MetricCard label="Total Tracked" value={analytics.total_tracked} />
        <MetricCard label="Active" value={analytics.active_total} />
        <MetricCard label="Needs Resume" value={analytics.needs_resume_count} />
        <MetricCard label="Applied" value={analytics.applied_count} />
        <MetricCard label="Interviewing" value={analytics.interviewing_count} />
        <MetricCard label="Offers" value={analytics.offer_count} />
      </div>

      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <MetricCard label="Ready to Apply" value={analytics.jobs_ready_to_apply} tone="success" />
        <MetricCard label="Needs Resume" value={analytics.needs_resume_count} tone="warning" />
        <MetricCard label="Needs Cold DM" value={analytics.needs_cold_dm_count} tone="warning" />
        <MetricCard label="Stale Applications" value={analytics.stale_applications} tone="danger" />
      </div>

      <div className="grid gap-4 xl:grid-cols-[1fr_1fr_1fr_1.2fr]">
        <Panel title="Conversion">
          <ProgressRow label="Applied Rate" value={analytics.conversion_summary.applied_rate} text={analytics.conversion_summary.applied_label} />
          <ProgressRow label="Interview Rate" value={analytics.conversion_summary.interview_rate} text={analytics.conversion_summary.interview_label} />
          <ProgressRow label="Offer Rate" value={analytics.conversion_summary.offer_rate} text={analytics.conversion_summary.offer_label} />
          <ProgressRow label="Rejection Rate" value={analytics.conversion_summary.rejection_rate} text={analytics.conversion_summary.rejection_label} />
        </Panel>
        <Panel title="By Priority">
          <BreakdownRows rows={analytics.priority_breakdown} max={analytics.total_tracked} formatter={labelize} />
        </Panel>
        <Panel title="By Match Tier">
          <BreakdownRows rows={analytics.match_tier_breakdown} max={analytics.total_tracked} formatter={formatTierLabel} />
        </Panel>
        <Panel title="By Status">
          <BreakdownRows rows={analytics.status_breakdown} max={analytics.total_tracked} formatter={formatStatusLabel} />
        </Panel>
      </div>

      <Panel title="Needs Action">
        {analytics.needs_action_items.length > 0 ? (
          <div className="grid gap-2 lg:grid-cols-2 xl:grid-cols-5">
            {analytics.needs_action_items.map((item) => (
              <div key={item.decision.id} className="rounded border border-[#edf0f5] bg-[#fcfcfd] p-3">
                <div className="text-sm font-semibold leading-5 text-[#171923]">
                  {item.decision.title ?? item.decision.job_title ?? "Tracked job"}
                </div>
                <p className="mt-1 text-xs text-[#667085]">{item.decision.company_name ?? "Unknown company"}</p>
                <p className="mt-2 text-xs font-medium text-[#9a3412]">{item.reason}</p>
                <p className="mt-1 text-xs text-[#475467]">{formatStatusLabel(item.decision.decision_status ?? item.decision.status ?? "saved")}</p>
                <Link
                  href={`/jobs/${item.decision.job_id}/workspace`}
                  className="mt-3 inline-block rounded border border-[#c8ced8] bg-white px-2 py-1.5 text-xs font-medium text-[#344054] hover:bg-[#f8fafc]"
                >
                  Open Workspace
                </Link>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-sm text-[#667085]">No urgent application actions detected.</p>
        )}
      </Panel>
    </section>
  );
}

function MetricCard({
  label,
  value,
  tone = "neutral",
}: {
  label: string;
  value: number;
  tone?: "neutral" | "success" | "warning" | "danger";
}) {
  const classes = {
    neutral: "border-[#d9dee8] bg-white text-[#171923]",
    success: "border-[#bbf7d0] bg-[#f0fdf4] text-[#166534]",
    warning: "border-[#fed7aa] bg-[#fff7ed] text-[#9a3412]",
    danger: "border-[#fecaca] bg-[#fff7f7] text-[#991b1b]",
  }[tone];
  return (
    <div className={`rounded-md border p-4 ${classes}`}>
      <div className="text-xs font-medium uppercase tracking-normal opacity-80">{label}</div>
      <div className="mt-2 text-2xl font-semibold">{value}</div>
    </div>
  );
}

function Panel({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div className="rounded-md border border-[#d9dee8] bg-white p-4">
      <h3 className="text-sm font-semibold text-[#171923]">{title}</h3>
      <div className="mt-3 space-y-3">{children}</div>
    </div>
  );
}

function ProgressRow({ label, value, text }: { label: string; value: number; text: string }) {
  return (
    <div>
      <div className="flex items-center justify-between gap-3 text-sm">
        <span className="text-[#344054]">{label}</span>
        <span className="font-medium text-[#171923]">{text}</span>
      </div>
      <div className="mt-1 h-2 rounded-full bg-[#edf0f5]">
        <div className="h-2 rounded-full bg-[#172033]" style={{ width: `${Math.min(Math.max(value, 0), 100)}%` }} />
      </div>
    </div>
  );
}

function BreakdownRows({
  rows,
  max,
  formatter,
}: {
  rows: Array<{ label: string; value: number }>;
  max: number;
  formatter: (value: string) => string;
}) {
  const visibleRows = rows.filter((row) => row.value > 0);
  if (visibleRows.length === 0) {
    return <p className="text-sm text-[#667085]">No data yet.</p>;
  }
  return (
    <>
      {visibleRows.map((row) => (
        <ProgressRow
          key={row.label}
          label={formatter(row.label)}
          value={max > 0 ? Math.round((row.value / max) * 100) : 0}
          text={String(row.value)}
        />
      ))}
    </>
  );
}

function formatTierLabel(value: string) {
  return value === "unscored" ? "Unscored" : formatMatchTier(value);
}

function formatStatusLabel(value: string) {
  return decisionStatusLabel(value);
}
