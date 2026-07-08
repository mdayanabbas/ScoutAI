"use client";

import Link from "next/link";

import {
  formatExperience,
  formatJobDate,
  formatJobLabel,
  formatSalary,
  isValidJobUrl,
  shortCompanyId,
} from "@/components/jobs/job-format";
import { useJob } from "@/hooks/use-jobs";
import type { Job } from "@/types/job";

export function JobDetails({ jobId }: { jobId: string }) {
  const jobQuery = useJob(jobId);

  if (jobQuery.isLoading) {
    return <div className="h-40 animate-pulse rounded bg-[#eef2f6]" />;
  }

  if (jobQuery.error) {
    return (
      <div className="rounded-md border border-[#fecaca] bg-[#fff7f7] p-3 text-sm text-[#991b1b]">
        {jobQuery.error instanceof Error
          ? jobQuery.error.message
          : "Job details could not load."}
      </div>
    );
  }

  if (!jobQuery.data) {
    return null;
  }

  return <JobDetailsContent job={jobQuery.data} />;
}

function JobDetailsContent({ job }: { job: Job }) {
  const canOpenJob = isValidJobUrl(job.job_url);

  return (
    <div className="space-y-5">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h3 className="text-lg font-semibold text-[#171923]">{job.title}</h3>
          <div className="mt-2 flex flex-wrap gap-2 text-sm text-[#667085]">
            <Link
              href={`/companies/${job.company_id}`}
              className="text-[#175cd3] hover:underline"
            >
              Company {shortCompanyId(job.company_id)}
            </Link>
            <span>{formatJobLabel(job.role_category)}</span>
            <span>{job.location ?? "Not specified"}</span>
          </div>
        </div>
        {canOpenJob ? (
          <a
            href={job.job_url ?? undefined}
            target="_blank"
            rel="noopener noreferrer"
            className="rounded bg-[#172033] px-3 py-2 text-sm font-medium text-white hover:bg-[#24314a]"
          >
            Open Job
          </a>
        ) : null}
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <DetailItem label="Role Category" value={formatJobLabel(job.role_category)} />
        <DetailItem label="Remote Type" value={formatJobLabel(job.remote_type)} />
        <DetailItem label="Experience" value={formatExperience(job)} />
        <DetailItem label="Salary" value={formatSalary(job)} />
        <DetailItem label="Status" value={formatJobLabel(job.status)} />
        <DetailItem label="Source Platform" value={job.source_platform ?? "Unknown"} />
        <DetailItem label="First Seen" value={formatJobDate(job.first_seen_at)} />
        <DetailItem label="Last Seen" value={formatJobDate(job.last_seen_at)} />
        <DetailItem label="Created" value={formatJobDate(job.created_at)} />
        <DetailItem label="Updated" value={formatJobDate(job.updated_at)} />
      </div>

      <div>
        <h4 className="text-sm font-semibold text-[#171923]">Description</h4>
        <div className="mt-2 max-h-96 overflow-auto whitespace-pre-wrap rounded-md border border-[#edf0f5] bg-[#f8fafc] p-3 text-sm leading-6 text-[#475467]">
          {job.description ?? "No description available."}
        </div>
      </div>

      <div>
        <h4 className="text-sm font-semibold text-[#171923]">Job URL</h4>
        <p className="mt-2 break-all text-sm text-[#475467]">
          {job.job_url ?? "Not specified"}
        </p>
      </div>
    </div>
  );
}

function DetailItem({ label, value }: { label: string; value: string | number }) {
  return (
    <div>
      <dt className="text-xs font-medium uppercase text-[#667085]">{label}</dt>
      <dd className="mt-1 break-words text-sm text-[#171923]">{value}</dd>
    </div>
  );
}
