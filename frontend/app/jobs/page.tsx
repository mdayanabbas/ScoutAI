"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useEffect, useMemo, useState, type ReactNode } from "react";

import { JobDetails } from "@/components/jobs/JobDetails";
import { JobTable } from "@/components/jobs/JobTable";
import { PageHeader } from "@/components/layout/PageHeader";
import { useJobs } from "@/hooks/use-jobs";
import type {
  JobListParams,
  JobStatus,
  RemoteType,
  RoleCategory,
} from "@/types/job";

const roleOptions: Array<{ value: "" | RoleCategory; label: string }> = [
  { value: "", label: "All roles" },
  { value: "ai_engineer", label: "AI Engineer" },
  { value: "backend_engineer", label: "Backend Engineer" },
  { value: "software_engineer", label: "Software Engineer" },
  { value: "ml_engineer", label: "ML Engineer" },
  { value: "data_engineer", label: "Data Engineer" },
  { value: "full_stack_engineer", label: "Full Stack Engineer" },
  { value: "frontend_engineer", label: "Frontend Engineer" },
  { value: "devops_engineer", label: "DevOps Engineer" },
  { value: "product_engineer", label: "Product Engineer" },
  { value: "other", label: "Other" },
];

const remoteOptions: Array<{ value: "" | RemoteType; label: string }> = [
  { value: "", label: "All remote types" },
  { value: "unknown", label: "Unknown" },
  { value: "onsite", label: "Onsite" },
  { value: "hybrid", label: "Hybrid" },
  { value: "remote_country", label: "Remote Country" },
  { value: "remote_region", label: "Remote Region" },
  { value: "remote_worldwide", label: "Remote Worldwide" },
];

const statusOptions: Array<{ value: "" | JobStatus; label: string }> = [
  { value: "", label: "All statuses" },
  { value: "active", label: "Active" },
  { value: "inactive", label: "Inactive" },
  { value: "expired", label: "Expired" },
  { value: "unknown", label: "Unknown" },
];

const pageSizeOptions = [10, 20, 50];

function numberParam(value: string | null, fallback: number) {
  const parsed = Number(value);
  return Number.isInteger(parsed) && parsed > 0 ? parsed : fallback;
}

function pageSizeParam(value: string | null) {
  const parsed = numberParam(value, 20);
  return pageSizeOptions.includes(parsed) ? parsed : 20;
}

function optionValue<T extends string>(
  value: string | null,
  options: Array<{ value: "" | T; label: string }>,
) {
  return options.some((option) => option.value === value) ? (value as T) : "";
}

export default function JobsPage() {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const [selectedJobId, setSelectedJobId] = useState<string | null>(null);

  const page = numberParam(searchParams.get("page"), 1);
  const pageSize = pageSizeParam(searchParams.get("page_size"));
  const search = searchParams.get("search") ?? "";
  const roleCategory = optionValue<RoleCategory>(
    searchParams.get("role_category"),
    roleOptions,
  );
  const remoteType = optionValue<RemoteType>(
    searchParams.get("remote_type"),
    remoteOptions,
  );
  const status = optionValue<JobStatus>(searchParams.get("status"), statusOptions);
  const [searchInput, setSearchInput] = useState(search);

  const params = useMemo<JobListParams>(
    () => ({
      page,
      page_size: pageSize,
      search: search || undefined,
      role_category: roleCategory || undefined,
      remote_type: remoteType || undefined,
      status: status || undefined,
    }),
    [page, pageSize, search, roleCategory, remoteType, status],
  );
  const jobsQuery = useJobs(params);
  const jobs = jobsQuery.data?.items ?? [];
  const hasFilters = Boolean(search || roleCategory || remoteType || status);

  useEffect(() => {
    setSearchInput(search);
  }, [search]);

  useEffect(() => {
    const handle = window.setTimeout(() => {
      if (searchInput === search) {
        return;
      }
      updateParams({ search: searchInput.trim(), page: "1" });
    }, 350);

    return () => window.clearTimeout(handle);
  }, [searchInput, search]);

  function replaceParams(nextValues: Record<string, string | number | null>) {
    const next = new URLSearchParams(searchParams.toString());

    Object.entries(nextValues).forEach(([key, value]) => {
      if (value === null || value === "") {
        next.delete(key);
      } else {
        next.set(key, String(value));
      }
    });

    const queryString = next.toString();
    router.replace(queryString ? `${pathname}?${queryString}` : pathname);
  }

  function updateParams(nextValues: Record<string, string | number | null>) {
    replaceParams(nextValues);
  }

  function updateFilter(key: string, value: string) {
    updateParams({ [key]: value, page: "1" });
  }

  function clearFilters() {
    setSearchInput("");
    replaceParams({
      page: null,
      page_size: 20,
      search: null,
      role_category: null,
      remote_type: null,
      status: null,
    });
  }

  return (
    <>
      <PageHeader
        title="Jobs"
        description="Browse manually tracked jobs across all companies."
        actions={
          <div className="rounded border border-[#d9dee8] bg-white px-3 py-2 text-sm text-[#475467]">
            {jobsQuery.data?.total ?? 0} total jobs
          </div>
        }
      />

      <section className="mb-5 rounded-md border border-[#d9dee8] bg-white p-4">
        <div className="grid gap-4 lg:grid-cols-[1.5fr_1fr_1fr_1fr_auto]">
          <label className="block">
            <span className="mb-1.5 block text-sm font-medium text-[#344054]">
              Search
            </span>
            <input
              value={searchInput}
              onChange={(event) => setSearchInput(event.target.value)}
              placeholder="Search job titles"
              className="w-full rounded border border-[#c8ced8] px-3 py-2 text-sm outline-none focus:border-[#172033]"
            />
          </label>

          <SelectField
            label="Role Category"
            value={roleCategory}
            options={roleOptions}
            onChange={(value) => updateFilter("role_category", value)}
          />
          <SelectField
            label="Remote Type"
            value={remoteType}
            options={remoteOptions}
            onChange={(value) => updateFilter("remote_type", value)}
          />
          <SelectField
            label="Status"
            value={status}
            options={statusOptions}
            onChange={(value) => updateFilter("status", value)}
          />

          <div className="flex items-end">
            <button
              type="button"
              onClick={clearFilters}
              className="h-[38px] rounded border border-[#c8ced8] bg-white px-3 text-sm font-medium text-[#344054] hover:bg-[#f8fafc]"
            >
              Clear Filters
            </button>
          </div>
        </div>
      </section>

      {jobsQuery.isLoading ? <LoadingState /> : null}

      {jobsQuery.error ? (
        <div className="rounded-md border border-[#fecaca] bg-[#fff7f7] p-4">
          <h2 className="text-sm font-semibold text-[#991b1b]">
            Jobs could not load
          </h2>
          <p className="mt-1 text-sm text-[#7f1d1d]">
            {jobsQuery.error instanceof Error
              ? jobsQuery.error.message
              : "Check the backend API."}
          </p>
          <button
            type="button"
            onClick={() => jobsQuery.refetch()}
            className="mt-4 rounded bg-[#172033] px-3 py-2 text-sm font-medium text-white"
          >
            Retry
          </button>
        </div>
      ) : null}

      {!jobsQuery.isLoading && !jobsQuery.error && jobs.length === 0 ? (
        <EmptyState
          message={
            hasFilters
              ? "No jobs match the selected filters."
              : "No jobs have been added yet."
          }
          action={hasFilters ? <ClearFiltersButton onClick={clearFilters} /> : null}
        />
      ) : null}

      {!jobsQuery.error && jobs.length > 0 ? (
        <div className="space-y-4">
          {jobsQuery.isFetching ? (
            <div className="text-sm text-[#667085]">Updating jobs...</div>
          ) : null}
          <JobTable jobs={jobs} onView={setSelectedJobId} />
          <Pagination
            page={jobsQuery.data?.page ?? page}
            pageSize={jobsQuery.data?.page_size ?? pageSize}
            total={jobsQuery.data?.total ?? 0}
            hasPrev={jobsQuery.data?.has_prev ?? page > 1}
            hasNext={jobsQuery.data?.has_next ?? false}
            onPageChange={(nextPage) => updateParams({ page: nextPage })}
            onPageSizeChange={(nextPageSize) =>
              updateParams({ page_size: nextPageSize, page: "1" })
            }
          />
        </div>
      ) : null}

      {selectedJobId ? (
        <Modal title="Job Details" onClose={() => setSelectedJobId(null)}>
          <JobDetails jobId={selectedJobId} />
        </Modal>
      ) : null}
    </>
  );
}

function SelectField<T extends string>({
  label,
  value,
  options,
  onChange,
}: {
  label: string;
  value: "" | T;
  options: Array<{ value: "" | T; label: string }>;
  onChange: (value: string) => void;
}) {
  return (
    <label className="block">
      <span className="mb-1.5 block text-sm font-medium text-[#344054]">
        {label}
      </span>
      <select
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="w-full rounded border border-[#c8ced8] px-3 py-2 text-sm outline-none focus:border-[#172033]"
      >
        {options.map((option) => (
          <option key={option.value || "all"} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </label>
  );
}

function LoadingState() {
  return (
    <div className="space-y-3">
      {Array.from({ length: 5 }).map((_, index) => (
        <div
          key={index}
          className="h-20 animate-pulse rounded-md border border-[#d9dee8] bg-white"
        />
      ))}
    </div>
  );
}

function EmptyState({
  message,
  action,
}: {
  message: string;
  action?: ReactNode;
}) {
  return (
    <div className="rounded-md border border-dashed border-[#c8ced8] bg-white p-8 text-center">
      <p className="text-sm text-[#667085]">{message}</p>
      {action ? <div className="mt-4">{action}</div> : null}
    </div>
  );
}

function ClearFiltersButton({ onClick }: { onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="rounded border border-[#c8ced8] bg-white px-3 py-2 text-sm font-medium text-[#344054] hover:bg-[#f8fafc]"
    >
      Clear Filters
    </button>
  );
}

function Pagination({
  page,
  pageSize,
  total,
  hasPrev,
  hasNext,
  onPageChange,
  onPageSizeChange,
}: {
  page: number;
  pageSize: number;
  total: number;
  hasPrev: boolean;
  hasNext: boolean;
  onPageChange: (page: number) => void;
  onPageSizeChange: (pageSize: number) => void;
}) {
  const firstItem = total === 0 ? 0 : (page - 1) * pageSize + 1;
  const lastItem = Math.min(page * pageSize, total);

  return (
    <div className="flex flex-col gap-3 rounded-md border border-[#d9dee8] bg-white px-4 py-3 text-sm text-[#475467] sm:flex-row sm:items-center sm:justify-between">
      <div>
        Showing {firstItem}-{lastItem} of {total} results
      </div>
      <div className="flex flex-wrap items-center gap-3">
        <label className="flex items-center gap-2">
          <span>Page size</span>
          <select
            value={pageSize}
            onChange={(event) => onPageSizeChange(Number(event.target.value))}
            className="rounded border border-[#c8ced8] px-2 py-1 text-sm outline-none focus:border-[#172033]"
          >
            {pageSizeOptions.map((option) => (
              <option key={option} value={option}>
                {option}
              </option>
            ))}
          </select>
        </label>
        <span>Page {page}</span>
        <button
          type="button"
          onClick={() => onPageChange(page - 1)}
          disabled={!hasPrev}
          className="rounded border border-[#c8ced8] bg-white px-3 py-1.5 font-medium text-[#344054] hover:bg-[#f8fafc] disabled:cursor-not-allowed disabled:opacity-50"
        >
          Previous
        </button>
        <button
          type="button"
          onClick={() => onPageChange(page + 1)}
          disabled={!hasNext}
          className="rounded border border-[#c8ced8] bg-white px-3 py-1.5 font-medium text-[#344054] hover:bg-[#f8fafc] disabled:cursor-not-allowed disabled:opacity-50"
        >
          Next
        </button>
      </div>
    </div>
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
      <div className="mx-auto max-w-4xl rounded-md bg-white shadow-xl">
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
