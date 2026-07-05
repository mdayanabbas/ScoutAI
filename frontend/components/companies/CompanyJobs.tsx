import type { Job } from "@/types/job";
import {
  EmptyState,
  formatLabel,
  SectionError,
  SectionShell,
  StatusBadge,
} from "@/components/companies/detail-format";

function experienceRange(job: Job) {
  if (job.experience_min === null && job.experience_max === null) {
    return "None";
  }
  return `${job.experience_min ?? "Any"} - ${job.experience_max ?? "Any"}`;
}

export function CompanyJobs({
  jobs,
  error,
}: {
  jobs?: Job[];
  error?: Error | null;
}) {
  return (
    <SectionShell title="Jobs">
      {error ? <SectionError message={error.message} /> : null}
      {!error && jobs?.length === 0 ? <EmptyState message="No jobs found." /> : null}
      {!error && jobs && jobs.length > 0 ? (
        <div className="space-y-3">
          {jobs.map((job) => (
            <article
              key={job.id}
              className="rounded-md border border-[#edf0f5] p-4"
            >
              <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
                <div>
                  <h3 className="text-sm font-semibold text-[#171923]">
                    {job.title}
                  </h3>
                  <p className="mt-1 text-sm text-[#667085]">
                    {formatLabel(job.role_category)} · {job.location ?? "None"} ·{" "}
                    {formatLabel(job.remote_type)}
                  </p>
                </div>
                <StatusBadge value={job.status} />
              </div>
              <div className="mt-3 grid gap-3 text-sm text-[#475467] sm:grid-cols-2 lg:grid-cols-4">
                <span>Experience: {experienceRange(job)}</span>
                <span>Remote: {formatLabel(job.remote_type)}</span>
                <span>Role: {formatLabel(job.role_category)}</span>
                <a
                  href={job.job_url ?? "#"}
                  target="_blank"
                  rel="noreferrer"
                  className="truncate text-[#175cd3] hover:underline"
                >
                  {job.job_url ?? "No URL"}
                </a>
              </div>
            </article>
          ))}
        </div>
      ) : null}
    </SectionShell>
  );
}
