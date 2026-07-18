"use client";

import Link from "next/link";

import {
  formatMatchTier,
  formatRemoteEligibility,
  formatSalary,
  normalizeExternalUrl,
} from "@/components/recommendations/recommendation-format";
import type { RemoteDiscoveryTopRecommendation } from "@/types/discovery";

export function DiscoveryTopRecommendations({
  recommendations,
  selectedSources,
  sourceScoped,
}: {
  recommendations: RemoteDiscoveryTopRecommendation[];
  selectedSources: string[];
  sourceScoped: boolean;
}) {
  if (!recommendations.length) {
    return (
      <section className="rounded-md border border-[#d9dee8] bg-white p-5">
        <h2 className="text-base font-semibold text-[#171923]">Top Recommendations</h2>
        <p className="mt-2 text-sm text-[#667085]">
          No recommendations returned for this run. Check source diagnostics to see whether jobs were fetched, enriched, scored, or filtered out.
        </p>
      </section>
    );
  }

  return (
    <section className="rounded-md border border-[#d9dee8] bg-white p-5">
      <div className="mb-4">
        <h2 className="text-base font-semibold text-[#171923]">Top Recommendations</h2>
        <p className="mt-1 text-sm text-[#667085]">
          Showing recommendations returned by the backend for this run.
        </p>
      </div>

      {selectedSources.length && !sourceScoped ? (
        <div className="mb-4 rounded border border-[#fedf89] bg-[#fffbeb] px-3 py-2 text-sm text-[#92400e]">
          Recommendations may include jobs outside the selected source. Backend recommendation scoping may need verification.
        </div>
      ) : null}

      <div className="space-y-3">
        {recommendations.map((job, index) => {
          const jobId = job.job_id ?? "";
          const external = normalizeExternalUrl(job.apply_url) ?? normalizeExternalUrl(job.job_url);
          const salary = formatSalary({
            salary_min: job.salary_min,
            salary_max: job.salary_max,
            salary_currency: job.salary_currency,
          });
          return (
            <article key={jobId || index} className="rounded border border-[#e4e7ec] bg-[#fcfcfd] p-4">
              <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
                <div>
                  <h3 className="text-base font-semibold text-[#171923]">
                    {job.title ?? "Untitled job"}
                  </h3>
                  <p className="mt-1 text-sm text-[#667085]">{job.company_name ?? "Unknown company"}</p>
                  <div className="mt-2 flex flex-wrap gap-2 text-xs text-[#475467]">
                    <span className="rounded bg-white px-2 py-1 ring-1 ring-[#e4e7ec]">
                      Score {job.total_score ?? 0}
                    </span>
                    <span className="rounded bg-white px-2 py-1 ring-1 ring-[#e4e7ec]">
                      {job.eligibility_status ?? "unknown"}
                    </span>
                    <span className="rounded bg-white px-2 py-1 ring-1 ring-[#e4e7ec]">
                      {formatMatchTier(job.match_tier ?? "unknown")}
                    </span>
                    <span className="rounded bg-white px-2 py-1 ring-1 ring-[#e4e7ec]">
                      {formatRemoteEligibility(job.remote_eligibility ?? "unknown")}
                    </span>
                    {salary ? (
                      <span className="rounded bg-white px-2 py-1 ring-1 ring-[#e4e7ec]">
                        {salary}
                      </span>
                    ) : null}
                  </div>
                  {job.eligibility_reason ? (
                    <p className="mt-3 text-sm leading-6 text-[#344054]">{job.eligibility_reason}</p>
                  ) : null}
                </div>
                <div className="flex shrink-0 flex-wrap gap-2">
                  {external ? (
                    <a
                      href={external}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="rounded border border-[#c8ced8] bg-white px-3 py-2 text-sm font-medium text-[#344054] hover:bg-[#f8fafc]"
                    >
                      Open Job
                    </a>
                  ) : null}
                  {jobId ? (
                    <>
                      <Link
                        href={`/jobs/${jobId}/workspace`}
                        className="rounded bg-[#172033] px-3 py-2 text-sm font-medium text-white hover:bg-[#0f1728]"
                      >
                        Open Workspace
                      </Link>
                      <Link
                        href="/recommendations"
                        className="rounded border border-[#c8ced8] bg-white px-3 py-2 text-sm font-medium text-[#344054] hover:bg-[#f8fafc]"
                      >
                        View Recommended Job
                      </Link>
                    </>
                  ) : null}
                </div>
              </div>
            </article>
          );
        })}
      </div>
    </section>
  );
}
