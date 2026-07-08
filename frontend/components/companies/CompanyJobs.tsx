"use client";

import { useState, type ReactNode } from "react";

import {
  EmptyState,
  formatDateTime,
  formatLabel,
  SectionError,
  SectionShell,
  StatusBadge,
} from "@/components/companies/detail-format";
import { JobForm } from "@/components/jobs/JobForm";
import {
  useCreateCompanyJob,
  useDeleteJob,
  useJob,
  useUpdateJob,
} from "@/hooks/use-jobs";
import type {
  Job,
  JobCreateInput,
  JobListItem,
  JobUpdateInput,
} from "@/types/job";

function experienceRange(job: JobListItem) {
  if (job.experience_min === null && job.experience_max === null) {
    return "None";
  }
  return `${job.experience_min ?? "Any"} - ${job.experience_max ?? "Any"}`;
}

export function CompanyJobs({
  companyId,
  jobs,
  isLoading = false,
  error,
}: {
  companyId: string;
  jobs?: JobListItem[];
  isLoading?: boolean;
  error?: Error | null;
}) {
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [viewingJobId, setViewingJobId] = useState<string | null>(null);
  const [editingJob, setEditingJob] = useState<JobListItem | null>(null);
  const [deletingJob, setDeletingJob] = useState<JobListItem | null>(null);
  const createJob = useCreateCompanyJob(companyId);
  const updateJob = useUpdateJob();
  const deleteJob = useDeleteJob(companyId);
  const jobDetail = useJob(viewingJobId);

  function openCreate() {
    createJob.reset();
    setIsCreateOpen(true);
  }

  function closeCreate() {
    createJob.reset();
    setIsCreateOpen(false);
  }

  async function handleCreateJob(input: JobCreateInput) {
    await createJob.mutateAsync(input);
    closeCreate();
  }

  function openEdit(job: JobListItem) {
    updateJob.reset();
    setEditingJob(job);
  }

  function closeEdit() {
    updateJob.reset();
    setEditingJob(null);
  }

  async function handleUpdateJob(input: JobUpdateInput) {
    if (!editingJob) {
      return;
    }

    await updateJob.mutateAsync({
      jobId: editingJob.id,
      companyId,
      data: input,
    });
    closeEdit();
  }

  function openDelete(job: JobListItem) {
    deleteJob.reset();
    setDeletingJob(job);
  }

  function closeDelete() {
    deleteJob.reset();
    setDeletingJob(null);
  }

  async function handleDeleteJob() {
    if (!deletingJob) {
      return;
    }

    await deleteJob.mutateAsync(deletingJob.id);
    closeDelete();
  }

  return (
    <SectionShell title="Jobs">
      <div className="mb-4 flex items-center justify-between gap-3">
        <p className="text-sm text-[#667085]">
          Manually tracked jobs for this company.
        </p>
        <button
          type="button"
          onClick={openCreate}
          className="rounded bg-[#172033] px-3 py-2 text-sm font-medium text-white hover:bg-[#24314a]"
        >
          Add Job
        </button>
      </div>

      {isLoading ? (
        <div className="space-y-3">
          {Array.from({ length: 3 }).map((_, index) => (
            <div
              key={index}
              className="h-20 animate-pulse rounded bg-[#eef2f6]"
            />
          ))}
        </div>
      ) : null}

      {error ? <SectionError message={error.message} /> : null}
      {!isLoading && !error && jobs?.length === 0 ? (
        <EmptyState message="No jobs found." />
      ) : null}
      {!isLoading && !error && jobs && jobs.length > 0 ? (
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
                    {formatLabel(job.role_category)} - {job.location ?? "None"} -{" "}
                    {formatLabel(job.remote_type)}
                  </p>
                </div>
                <StatusBadge value={job.status} />
              </div>
              <div className="mt-3 grid gap-3 text-sm text-[#475467] sm:grid-cols-2 lg:grid-cols-5">
                <span>Experience: {experienceRange(job)}</span>
                <span>Remote: {formatLabel(job.remote_type)}</span>
                <span>Role: {formatLabel(job.role_category)}</span>
                <span>Created: {formatDateTime(job.created_at)}</span>
                <a
                  href={job.job_url ?? "#"}
                  target="_blank"
                  rel="noreferrer"
                  className="truncate text-[#175cd3] hover:underline"
                >
                  {job.job_url ?? "No URL"}
                </a>
              </div>
              <div className="mt-4 flex flex-wrap justify-end gap-2">
                <a
                  href={job.job_url ?? "#"}
                  target="_blank"
                  rel="noreferrer"
                  className="rounded border border-[#c8ced8] bg-white px-2.5 py-1.5 text-xs font-medium text-[#344054] hover:bg-[#f8fafc]"
                >
                  Open
                </a>
                <button
                  type="button"
                  onClick={() => setViewingJobId(job.id)}
                  className="rounded border border-[#c8ced8] bg-white px-2.5 py-1.5 text-xs font-medium text-[#344054] hover:bg-[#f8fafc]"
                >
                  View
                </button>
                <button
                  type="button"
                  onClick={() => openEdit(job)}
                  className="rounded border border-[#c8ced8] bg-white px-2.5 py-1.5 text-xs font-medium text-[#344054] hover:bg-[#f8fafc]"
                >
                  Edit
                </button>
                <button
                  type="button"
                  onClick={() => openDelete(job)}
                  disabled={deleteJob.isPending && deletingJob?.id === job.id}
                  className="rounded border border-[#fca5a5] bg-white px-2.5 py-1.5 text-xs font-medium text-[#b42318] hover:bg-[#fff7f7] disabled:cursor-not-allowed disabled:opacity-60"
                >
                  {deleteJob.isPending && deletingJob?.id === job.id
                    ? "Deleting..."
                    : "Delete"}
                </button>
              </div>
            </article>
          ))}
        </div>
      ) : null}

      {isCreateOpen ? (
        <Modal title="Add Job" onClose={closeCreate}>
          <JobForm
            isSubmitting={createJob.isPending}
            submitError={createJob.error}
            onSubmit={handleCreateJob}
            onCancel={closeCreate}
          />
        </Modal>
      ) : null}

      {editingJob ? (
        <Modal title="Edit Job" onClose={closeEdit}>
          <JobForm
            mode="edit"
            initialValues={editingJob}
            isSubmitting={updateJob.isPending}
            submitError={updateJob.error}
            onSubmit={handleUpdateJob}
            onCancel={closeEdit}
          />
        </Modal>
      ) : null}

      {viewingJobId ? (
        <Modal title="Job Details" onClose={() => setViewingJobId(null)}>
          {jobDetail.isLoading ? (
            <div className="h-24 animate-pulse rounded bg-[#eef2f6]" />
          ) : null}
          {jobDetail.error ? (
            <SectionError
              message={
                jobDetail.error instanceof Error
                  ? jobDetail.error.message
                  : "Job could not load."
              }
            />
          ) : null}
          {jobDetail.data ? <JobDetail job={jobDetail.data} /> : null}
        </Modal>
      ) : null}

      {deletingJob ? (
        <div className="fixed inset-0 z-50 grid place-items-center bg-[#101828]/40 px-4 py-6">
          <div className="w-full max-w-md rounded-md bg-white p-5 shadow-xl">
            <h3 className="text-lg font-semibold text-[#171923]">
              Delete Job
            </h3>
            <p className="mt-2 text-sm leading-6 text-[#475467]">
              Delete {deletingJob.title}? This removes the manually tracked job
              from this company.
            </p>
            {deleteJob.error ? (
              <div className="mt-4 rounded-md border border-[#fecaca] bg-[#fff7f7] p-3 text-sm text-[#991b1b]">
                {deleteJob.error instanceof Error
                  ? deleteJob.error.message
                  : "Job could not be deleted."}
              </div>
            ) : null}
            <div className="mt-5 flex justify-end gap-3">
              <button
                type="button"
                onClick={closeDelete}
                disabled={deleteJob.isPending}
                className="rounded border border-[#c8ced8] bg-white px-4 py-2 text-sm font-medium text-[#344054] hover:bg-[#f8fafc] disabled:cursor-not-allowed disabled:opacity-60"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleDeleteJob}
                disabled={deleteJob.isPending}
                className="rounded bg-[#b42318] px-4 py-2 text-sm font-medium text-white hover:bg-[#991b1b] disabled:cursor-not-allowed disabled:opacity-60"
              >
                {deleteJob.isPending ? "Deleting..." : "Delete Job"}
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </SectionShell>
  );
}

function Modal({
  title,
  children,
  onClose,
}: {
  title: string;
  children: ReactNode;
  onClose: () => void;
}) {
  return (
    <div className="fixed inset-0 z-50 overflow-y-auto bg-[#101828]/40 px-4 py-6 sm:py-10">
      <div className="mx-auto max-w-3xl rounded-md bg-white shadow-xl">
        <div className="flex items-start justify-between gap-4 border-b border-[#edf0f5] px-5 py-4">
          <h3 className="text-lg font-semibold text-[#171923]">{title}</h3>
          <button
            type="button"
            onClick={onClose}
            className="rounded border border-[#c8ced8] px-2.5 py-1.5 text-sm text-[#475467] hover:bg-[#f8fafc]"
          >
            Close
          </button>
        </div>
        <div className="px-5 py-5">{children}</div>
      </div>
    </div>
  );
}

function JobDetail({ job }: { job: Job }) {
  const salary =
    job.salary_min === null && job.salary_max === null
      ? "None"
      : `${job.salary_currency ?? "USD"} ${job.salary_min ?? "Any"} - ${
          job.salary_max ?? "Any"
        }`;

  return (
    <div className="space-y-4">
      <div className="grid gap-4 sm:grid-cols-2">
        <DetailItem label="Title" value={job.title} />
        <DetailItem label="Role" value={formatLabel(job.role_category)} />
        <DetailItem label="Location" value={job.location ?? "None"} />
        <DetailItem label="Remote" value={formatLabel(job.remote_type)} />
        <DetailItem label="Experience" value={experienceRange(job)} />
        <DetailItem label="Salary" value={salary} />
        <DetailItem label="Source" value={job.source_platform ?? "None"} />
        <DetailItem label="Status" value={formatLabel(job.status)} />
        <DetailItem label="First Seen" value={formatDateTime(job.first_seen_at)} />
        <DetailItem label="Last Seen" value={formatDateTime(job.last_seen_at)} />
      </div>
      <div>
        <h4 className="text-sm font-semibold text-[#171923]">Description</h4>
        <div className="mt-2 max-h-80 overflow-auto whitespace-pre-wrap rounded-md border border-[#edf0f5] bg-[#f8fafc] p-3 text-sm leading-6 text-[#475467]">
          {job.description ?? "None"}
        </div>
      </div>
    </div>
  );
}

function DetailItem({
  label,
  value,
}: {
  label: string;
  value: string | number;
}) {
  return (
    <div>
      <dt className="text-xs font-medium uppercase text-[#667085]">{label}</dt>
      <dd className="mt-1 break-words text-sm text-[#171923]">{value}</dd>
    </div>
  );
}
