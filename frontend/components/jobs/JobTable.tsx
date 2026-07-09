"use client";

import Link from "next/link";

import {
  formatExperience,
  formatJobDate,
  formatJobLabel,
  normalizeJobUrl,
} from "@/components/jobs/job-format";
import type { JobListItem } from "@/types/job";

export function JobTable({
  jobs,
  onView,
}: {
  jobs: JobListItem[];
  onView: (jobId: string) => void;
}) {
  return (
    <div className="overflow-x-auto rounded-md border border-[#d9dee8] bg-white">
      <table className="min-w-[980px] w-full border-collapse text-left text-sm">
        <thead className="bg-[#f8fafc] text-xs font-semibold uppercase text-[#667085]">
          <tr>
            <th className="px-4 py-3">Job</th>
            <th className="px-4 py-3">Company</th>
            <th className="px-4 py-3">Role Category</th>
            <th className="px-4 py-3">Location</th>
            <th className="px-4 py-3">Remote</th>
            <th className="px-4 py-3">Experience</th>
            <th className="px-4 py-3">Status</th>
            <th className="px-4 py-3">First Seen</th>
            <th className="px-4 py-3 text-right">Actions</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-[#edf0f5]">
          {jobs.map((job) => {
            const jobUrl = normalizeJobUrl(job.job_url);
            const companyName = job.company_name ?? "Unknown company";

            return (
              <tr key={job.id} className="align-top">
                <td className="max-w-[260px] px-4 py-4">
                  <div className="font-medium text-[#171923]">{job.title}</div>
                  <div className="mt-1 truncate text-xs text-[#667085]">
                    {job.normalized_title ?? "No normalized title"}
                  </div>
                </td>
                <td className="px-4 py-4">
                  <Link
                    href={`/companies/${job.company_id}`}
                    className="text-[#175cd3] hover:underline"
                    title={companyName}
                  >
                    {companyName}
                  </Link>
                </td>
                <td className="px-4 py-4 text-[#475467]">
                  {formatJobLabel(job.role_category)}
                </td>
                <td className="px-4 py-4 text-[#475467]">
                  {job.location ?? "Not specified"}
                </td>
                <td className="px-4 py-4 text-[#475467]">
                  {formatJobLabel(job.remote_type)}
                </td>
                <td className="px-4 py-4 text-[#475467]">
                  {formatExperience(job)}
                </td>
                <td className="px-4 py-4">
                  <StatusBadge value={job.status} />
                </td>
                <td className="px-4 py-4 text-[#475467]">
                  {formatJobDate(job.first_seen_at)}
                </td>
                <td className="px-4 py-4">
                  <div className="flex justify-end gap-2">
                    <button
                      type="button"
                      onClick={() => onView(job.id)}
                      className="rounded border border-[#c8ced8] bg-white px-2.5 py-1.5 text-xs font-medium text-[#344054] hover:bg-[#f8fafc]"
                    >
                      View
                    </button>
                    {jobUrl ? (
                      <a
                        href={jobUrl}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="rounded border border-[#c8ced8] bg-white px-2.5 py-1.5 text-xs font-medium text-[#344054] hover:bg-[#f8fafc]"
                      >
                        Open Job
                      </a>
                    ) : null}
                  </div>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function StatusBadge({ value }: { value: string }) {
  const classes =
    value === "active"
      ? "border-[#bbf7d0] bg-[#f0fdf4] text-[#166534]"
      : value === "expired" || value === "inactive"
        ? "border-[#fecaca] bg-[#fff7f7] text-[#991b1b]"
        : "border-[#e5e7eb] bg-[#f8fafc] text-[#475467]";

  return (
    <span
      className={[
        "inline-flex rounded-full border px-2 py-0.5 text-xs font-medium",
        classes,
      ].join(" ")}
    >
      {formatJobLabel(value)}
    </span>
  );
}
