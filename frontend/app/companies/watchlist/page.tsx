"use client";

import Link from "next/link";
import { useMemo, useState, type FormEvent, type ReactNode } from "react";
import { useQuery } from "@tanstack/react-query";

import { PageHeader } from "@/components/layout/PageHeader";
import { APP_ROUTES } from "@/lib/app-routes";
import {
  archiveCompanyWatchlistItem,
  createCompanyWatchlistItem,
  deleteCompanyWatchlistItem,
  fetchCompanyWatchlist,
  fetchCompanyWatchlistJobs,
  fetchCompanyWatchlistStats,
  updateCompanyWatchlistItem,
} from "@/lib/company-watchlist-api";
import { formatMatchTier, labelize, normalizeExternalUrl, sourceAttribution } from "@/components/recommendations/recommendation-format";
import type {
  CompanyWatchlistCreate,
  CompanyWatchlistJob,
  CompanyWatchlistResponse,
  CompanyWatchlistStatsResponse,
  CompanyWatchlistUpdate,
} from "@/types/company-watchlist";

const statusOptions = ["watching", "interested", "contacted", "applied", "paused", "archived"];
const priorityOptions = ["high", "medium", "low"];
const remoteOptions = ["unknown", "remote_worldwide", "remote_india", "hybrid_possible"];
const juniorOptions = ["unknown", "strong", "moderate", "weak"];

export default function CompanyWatchlistPage() {
  const [includeArchived, setIncludeArchived] = useState(false);
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("");
  const [priority, setPriority] = useState("");
  const [remote, setRemote] = useState("");
  const [junior, setJunior] = useState("");
  const [tag, setTag] = useState("");
  const [hasRecommended, setHasRecommended] = useState(false);
  const [needsReview, setNeedsReview] = useState(false);
  const [sort, setSort] = useState("priority");
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [editing, setEditing] = useState<CompanyWatchlistResponse | null>(null);
  const [jobsItem, setJobsItem] = useState<CompanyWatchlistResponse | null>(null);
  const listQuery = useQuery({
    queryKey: ["company-watchlist", includeArchived],
    queryFn: () => fetchCompanyWatchlist({ limit: 100, include_archived: includeArchived }),
  });
  const statsQuery = useQuery({
    queryKey: ["company-watchlist", "stats"],
    queryFn: fetchCompanyWatchlistStats,
    retry: 1,
  });
  const items = useMemo(
    () =>
      sortItems(
        (listQuery.data?.items ?? []).filter((item) =>
          passesFilters(item, { search, status, priority, remote, junior, tag, hasRecommended, needsReview }),
        ),
        sort,
      ),
    [listQuery.data?.items, search, status, priority, remote, junior, tag, hasRecommended, needsReview, sort],
  );

  async function refresh() {
    await Promise.all([listQuery.refetch(), statsQuery.refetch()]);
  }

  async function createItem(payload: CompanyWatchlistCreate) {
    setError(null);
    setMessage(null);
    try {
      await createCompanyWatchlistItem(payload);
      setMessage("Company added to watchlist.");
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not add company.");
      throw err;
    }
  }

  async function updateItem(item: CompanyWatchlistResponse, payload: CompanyWatchlistUpdate) {
    setError(null);
    try {
      await updateCompanyWatchlistItem(item.id, payload);
      setEditing(null);
      setMessage("Watchlist item updated.");
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not update watchlist item.");
    }
  }

  async function markReviewed(item: CompanyWatchlistResponse) {
    await updateItem(item, { last_reviewed_at: new Date().toISOString() });
  }

  async function archiveItem(item: CompanyWatchlistResponse) {
    setError(null);
    try {
      await archiveCompanyWatchlistItem(item.id);
      setMessage("Company archived.");
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not archive company.");
    }
  }

  async function deleteItem(item: CompanyWatchlistResponse) {
    if (!window.confirm(`Delete ${item.company_name} from the watchlist?`)) return;
    setError(null);
    try {
      await deleteCompanyWatchlistItem(item.id);
      setMessage("Company deleted.");
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not delete company.");
    }
  }

  return (
    <>
      <PageHeader
        title="Company Watchlist"
        description="Track startups you like and review new opportunities from them."
        actions={
          <div className="flex flex-wrap gap-2">
            <Link href={APP_ROUTES.recommendedJobs} className="rounded border border-[#c8ced8] bg-white px-3 py-2 text-sm font-medium text-[#344054] hover:bg-[#f8fafc]">
              Recommended Jobs
            </Link>
            <Link href={APP_ROUTES.discovery} className="rounded border border-[#c8ced8] bg-white px-3 py-2 text-sm font-medium text-[#344054] hover:bg-[#f8fafc]">
              Discovery Control
            </Link>
            <Link href={APP_ROUTES.commandCenter} className="rounded border border-[#c8ced8] bg-white px-3 py-2 text-sm font-medium text-[#344054] hover:bg-[#f8fafc]">
              Command Center
            </Link>
            <Link href={APP_ROUTES.analytics} className="rounded border border-[#c8ced8] bg-white px-3 py-2 text-sm font-medium text-[#344054] hover:bg-[#f8fafc]">
              Analytics
            </Link>
            <Link href={APP_ROUTES.pipeline} className="rounded bg-[#172033] px-3 py-2 text-sm font-medium text-white hover:bg-[#0f1728]">
              Application Pipeline
            </Link>
          </div>
        }
      />

      <WatchlistStats stats={statsQuery.data} error={Boolean(statsQuery.error)} />

      {message ? <Notice tone="success">{message}</Notice> : null}
      {error ? <Notice tone="danger">{error}</Notice> : null}

      <section className="mb-5 rounded-md border border-[#d9dee8] bg-white p-5">
        <h2 className="text-base font-semibold text-[#171923]">Add Company</h2>
        <CompanyWatchlistCreateForm onSubmit={createItem} />
      </section>

      <WatchlistFilters
        search={search}
        status={status}
        priority={priority}
        remote={remote}
        junior={junior}
        tag={tag}
        sort={sort}
        includeArchived={includeArchived}
        hasRecommended={hasRecommended}
        needsReview={needsReview}
        onSearch={setSearch}
        onStatus={setStatus}
        onPriority={setPriority}
        onRemote={setRemote}
        onJunior={setJunior}
        onTag={setTag}
        onSort={setSort}
        onIncludeArchived={setIncludeArchived}
        onHasRecommended={setHasRecommended}
        onNeedsReview={setNeedsReview}
      />

      {listQuery.isLoading ? <LoadingState /> : null}
      {listQuery.error ? (
        <div className="rounded-md border border-[#fecaca] bg-[#fff7f7] p-4">
          <h2 className="text-sm font-semibold text-[#991b1b]">Company watchlist could not load</h2>
          <button type="button" onClick={() => listQuery.refetch()} className="mt-3 rounded bg-[#172033] px-3 py-2 text-sm font-medium text-white">
            Retry
          </button>
        </div>
      ) : null}

      {!listQuery.isLoading && !listQuery.error && items.length === 0 ? (
        <div className="rounded-md border border-dashed border-[#c8ced8] bg-white p-8 text-center">
          <h2 className="text-base font-semibold text-[#171923]">No companies watched yet.</h2>
          <p className="mt-2 text-sm text-[#667085]">Watch companies from recommended jobs or add one manually.</p>
        </div>
      ) : null}

      {items.length > 0 ? (
        <section className="space-y-4">
          {items.map((item) => (
            <CompanyWatchlistItemCard
              key={item.id}
              item={item}
              onEdit={setEditing}
              onViewJobs={setJobsItem}
              onMarkReviewed={markReviewed}
              onArchive={archiveItem}
              onDelete={deleteItem}
            />
          ))}
        </section>
      ) : null}

      {editing ? (
        <WatchlistEditModal item={editing} onClose={() => setEditing(null)} onSave={(payload) => updateItem(editing, payload)} />
      ) : null}

      {jobsItem ? <RelatedJobsPanel item={jobsItem} onClose={() => setJobsItem(null)} /> : null}
    </>
  );
}

function CompanyWatchlistCreateForm({ onSubmit }: { onSubmit: (payload: CompanyWatchlistCreate) => Promise<void> }) {
  const [form, setForm] = useState({
    company_name: "",
    company_domain: "",
    company_url: "",
    watch_status: "watching",
    priority: "medium",
    interest_reason: "",
    target_roles: "",
    preferred_locations: "",
    tags: "",
    remote_interest: "unknown",
    junior_friendliness_signal: "unknown",
    notes: "",
  });
  const [pending, setPending] = useState(false);
  const [validation, setValidation] = useState<string | null>(null);

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!form.company_name.trim()) {
      setValidation("Company name is required.");
      return;
    }
    setPending(true);
    setValidation(null);
    try {
      await onSubmit(toPayload(form));
      setForm({ ...form, company_name: "", company_domain: "", company_url: "", interest_reason: "", target_roles: "", preferred_locations: "", tags: "", notes: "" });
    } finally {
      setPending(false);
    }
  }

  return (
    <form onSubmit={submit} className="mt-4 grid gap-3 lg:grid-cols-3">
      <Input label="Company Name" value={form.company_name} onChange={(value) => setForm({ ...form, company_name: value })} />
      <Input label="Domain" value={form.company_domain} onChange={(value) => setForm({ ...form, company_domain: value })} />
      <Input label="URL" value={form.company_url} onChange={(value) => setForm({ ...form, company_url: value })} />
      <Select label="Priority" value={form.priority} options={priorityOptions} onChange={(value) => setForm({ ...form, priority: value })} />
      <Select label="Status" value={form.watch_status} options={statusOptions} onChange={(value) => setForm({ ...form, watch_status: value })} />
      <Select label="Remote Interest" value={form.remote_interest} options={remoteOptions} onChange={(value) => setForm({ ...form, remote_interest: value })} />
      <Input label="Target Roles" value={form.target_roles} onChange={(value) => setForm({ ...form, target_roles: value })} placeholder="AI Engineer, ML Engineer" />
      <Input label="Locations" value={form.preferred_locations} onChange={(value) => setForm({ ...form, preferred_locations: value })} />
      <Input label="Tags" value={form.tags} onChange={(value) => setForm({ ...form, tags: value })} />
      <Select label="Junior Signal" value={form.junior_friendliness_signal} options={juniorOptions} onChange={(value) => setForm({ ...form, junior_friendliness_signal: value })} />
      <label className="lg:col-span-2">
        <span className="mb-1 block text-xs font-medium uppercase tracking-normal text-[#667085]">Interest Reason</span>
        <input value={form.interest_reason} onChange={(event) => setForm({ ...form, interest_reason: event.target.value })} className="w-full rounded border border-[#c8ced8] px-3 py-2 text-sm" />
      </label>
      <label className="lg:col-span-3">
        <span className="mb-1 block text-xs font-medium uppercase tracking-normal text-[#667085]">Notes</span>
        <textarea value={form.notes} onChange={(event) => setForm({ ...form, notes: event.target.value })} rows={3} className="w-full rounded border border-[#c8ced8] px-3 py-2 text-sm" />
      </label>
      {validation ? <p className="text-sm text-[#991b1b] lg:col-span-3">{validation}</p> : null}
      <div className="lg:col-span-3">
        <button type="submit" disabled={pending} className="rounded bg-[#172033] px-4 py-2 text-sm font-medium text-white disabled:opacity-60">
          {pending ? "Adding..." : "Add to Watchlist"}
        </button>
      </div>
    </form>
  );
}

function WatchlistStats({ stats, error }: { stats?: CompanyWatchlistStatsResponse; error: boolean }) {
  if (error) return <Notice tone="danger">Watchlist stats unavailable.</Notice>;
  const cards = [
    ["Total", stats?.total ?? 0],
    ["Watching", stats?.watching ?? 0],
    ["Interested", stats?.interested ?? 0],
    ["Contacted", stats?.contacted ?? 0],
    ["Applied", stats?.applied ?? 0],
    ["High Priority", stats?.high_priority ?? 0],
    ["Recommended Jobs", stats?.with_recommended_jobs ?? 0],
    ["Needs Review", stats?.needs_review ?? 0],
  ];
  return (
    <section className="mb-5 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
      {cards.map(([label, value]) => (
        <div key={label} className="rounded-md border border-[#d9dee8] bg-white p-4">
          <div className="text-xs font-medium uppercase tracking-normal text-[#667085]">{label}</div>
          <div className="mt-2 text-2xl font-semibold text-[#171923]">{value}</div>
        </div>
      ))}
    </section>
  );
}

function WatchlistFilters(props: {
  search: string; status: string; priority: string; remote: string; junior: string; tag: string; sort: string; includeArchived: boolean; hasRecommended: boolean; needsReview: boolean;
  onSearch: (v: string) => void; onStatus: (v: string) => void; onPriority: (v: string) => void; onRemote: (v: string) => void; onJunior: (v: string) => void; onTag: (v: string) => void; onSort: (v: string) => void; onIncludeArchived: (v: boolean) => void; onHasRecommended: (v: boolean) => void; onNeedsReview: (v: boolean) => void;
}) {
  return (
    <section className="mb-5 rounded-md border border-[#d9dee8] bg-white p-4">
      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-6">
        <Input label="Search" value={props.search} onChange={props.onSearch} />
        <Select label="Status" value={props.status} options={statusOptions} onChange={props.onStatus} includeAll />
        <Select label="Priority" value={props.priority} options={priorityOptions} onChange={props.onPriority} includeAll />
        <Select label="Remote" value={props.remote} options={remoteOptions} onChange={props.onRemote} includeAll />
        <Select label="Junior" value={props.junior} options={juniorOptions} onChange={props.onJunior} includeAll />
        <Select label="Sort" value={props.sort} options={["priority", "updated", "jobs", "recommended", "company"]} onChange={props.onSort} />
        <Input label="Tag" value={props.tag} onChange={props.onTag} />
      </div>
      <div className="mt-3 flex flex-wrap gap-4 text-sm text-[#344054]">
        <Checkbox label="Has recommended jobs" checked={props.hasRecommended} onChange={props.onHasRecommended} />
        <Checkbox label="Needs review" checked={props.needsReview} onChange={props.onNeedsReview} />
        <Checkbox label="Include archived" checked={props.includeArchived} onChange={props.onIncludeArchived} />
      </div>
    </section>
  );
}

function CompanyWatchlistItemCard({ item, onEdit, onViewJobs, onMarkReviewed, onArchive, onDelete }: {
  item: CompanyWatchlistResponse; onEdit: (item: CompanyWatchlistResponse) => void; onViewJobs: (item: CompanyWatchlistResponse) => void; onMarkReviewed: (item: CompanyWatchlistResponse) => void; onArchive: (item: CompanyWatchlistResponse) => void; onDelete: (item: CompanyWatchlistResponse) => void;
}) {
  const url = normalizeExternalUrl(item.company_url ?? item.company_domain);
  return (
    <article className="rounded-md border border-[#d9dee8] bg-white p-5 shadow-sm">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <div className="flex flex-wrap gap-2">
            <Badge>{labelize(item.watch_status)}</Badge>
            <Badge>{labelize(item.priority)}</Badge>
            <Badge>{labelize(item.remote_interest)}</Badge>
            <Badge>{labelize(item.junior_friendliness_signal)}</Badge>
          </div>
          <h2 className="mt-3 text-lg font-semibold text-[#171923]">{item.company_name}</h2>
          <div className="mt-1 text-sm text-[#667085]">
            {url ? <a href={url} target="_blank" rel="noopener noreferrer" className="text-[#175cd3] hover:underline">{item.company_domain ?? item.company_url}</a> : item.company_domain ?? "No domain"}
          </div>
          {item.interest_reason ? <p className="mt-3 text-sm text-[#344054]">{item.interest_reason}</p> : null}
          {item.notes ? <p className="mt-2 line-clamp-2 text-sm text-[#667085]">{item.notes}</p> : null}
          <div className="mt-3 flex flex-wrap gap-2 text-xs text-[#475467]">
            {(item.tags ?? []).map((tag) => <span key={tag} className="rounded bg-[#f8fafc] px-2 py-1">{tag}</span>)}
            {(item.target_roles ?? []).map((role) => <span key={role} className="rounded bg-[#eff6ff] px-2 py-1">{role}</span>)}
          </div>
        </div>
        <dl className="grid gap-2 text-sm text-[#475467] sm:grid-cols-2 lg:w-96">
          <Fact label="Jobs" value={String(item.job_count ?? 0)} />
          <Fact label="Recommended" value={String(item.recommended_job_count ?? 0)} />
          <Fact label="Latest job" value={item.latest_job_title ?? "None"} />
          <Fact label="Latest published" value={formatDate(item.latest_job_published_at)} />
          <Fact label="Last reviewed" value={formatDate(item.last_reviewed_at)} />
        </dl>
      </div>
      <div className="mt-4 flex flex-wrap gap-2">
        <button type="button" onClick={() => onEdit(item)} className="rounded border border-[#c8ced8] px-3 py-2 text-sm font-medium text-[#344054]">Edit</button>
        <button type="button" onClick={() => onViewJobs(item)} className="rounded border border-[#175cd3] px-3 py-2 text-sm font-medium text-[#175cd3]">View Jobs</button>
        <button type="button" onClick={() => onMarkReviewed(item)} className="rounded border border-[#166534] px-3 py-2 text-sm font-medium text-[#166534]">Mark Reviewed</button>
        <button type="button" onClick={() => onArchive(item)} className="rounded border border-[#fed7aa] px-3 py-2 text-sm font-medium text-[#9a3412]">Archive</button>
        <button type="button" onClick={() => onDelete(item)} className="rounded border border-[#fecaca] px-3 py-2 text-sm font-medium text-[#991b1b]">Delete</button>
      </div>
    </article>
  );
}

function WatchlistEditModal({ item, onClose, onSave }: { item: CompanyWatchlistResponse; onClose: () => void; onSave: (payload: CompanyWatchlistUpdate) => Promise<void> }) {
  const [form, setForm] = useState({
    watch_status: item.watch_status ?? "watching",
    priority: item.priority ?? "medium",
    interest_reason: item.interest_reason ?? "",
    target_roles: (item.target_roles ?? []).join(", "),
    preferred_locations: (item.preferred_locations ?? []).join(", "),
    notes: item.notes ?? "",
    tags: (item.tags ?? []).join(", "),
    remote_interest: item.remote_interest ?? "unknown",
    junior_friendliness_signal: item.junior_friendliness_signal ?? "unknown",
  });
  const [pending, setPending] = useState(false);
  async function save() {
    setPending(true);
    try {
      await onSave(toPayload(form));
    } finally {
      setPending(false);
    }
  }
  return (
    <div className="fixed inset-0 z-50 overflow-y-auto bg-[#101828]/40 px-4 py-6">
      <div className="mx-auto max-w-3xl rounded-md bg-white p-5 shadow-xl">
        <div className="flex justify-between gap-4">
          <h2 className="text-lg font-semibold text-[#171923]">Edit {item.company_name}</h2>
          <button type="button" onClick={onClose} className="rounded border border-[#c8ced8] px-3 py-1.5 text-sm">Close</button>
        </div>
        <div className="mt-4 grid gap-3 md:grid-cols-2">
          <Select label="Status" value={form.watch_status} options={statusOptions} onChange={(value) => setForm({ ...form, watch_status: value })} />
          <Select label="Priority" value={form.priority} options={priorityOptions} onChange={(value) => setForm({ ...form, priority: value })} />
          <Select label="Remote Interest" value={form.remote_interest} options={remoteOptions} onChange={(value) => setForm({ ...form, remote_interest: value })} />
          <Select label="Junior Signal" value={form.junior_friendliness_signal} options={juniorOptions} onChange={(value) => setForm({ ...form, junior_friendliness_signal: value })} />
          <Input label="Target Roles" value={form.target_roles} onChange={(value) => setForm({ ...form, target_roles: value })} />
          <Input label="Locations" value={form.preferred_locations} onChange={(value) => setForm({ ...form, preferred_locations: value })} />
          <Input label="Tags" value={form.tags} onChange={(value) => setForm({ ...form, tags: value })} />
          <Input label="Interest Reason" value={form.interest_reason} onChange={(value) => setForm({ ...form, interest_reason: value })} />
          <label className="md:col-span-2">
            <span className="mb-1 block text-xs font-medium uppercase tracking-normal text-[#667085]">Notes</span>
            <textarea value={form.notes} onChange={(event) => setForm({ ...form, notes: event.target.value })} rows={4} className="w-full rounded border border-[#c8ced8] px-3 py-2 text-sm" />
          </label>
        </div>
        <div className="mt-5 flex justify-end gap-2">
          <button type="button" onClick={onClose} className="rounded border border-[#c8ced8] px-4 py-2 text-sm">Cancel</button>
          <button type="button" disabled={pending} onClick={save} className="rounded bg-[#172033] px-4 py-2 text-sm font-medium text-white disabled:opacity-60">{pending ? "Saving..." : "Save"}</button>
        </div>
      </div>
    </div>
  );
}

function RelatedJobsPanel({ item, onClose }: { item: CompanyWatchlistResponse; onClose: () => void }) {
  const jobsQuery = useQuery({
    queryKey: ["company-watchlist", item.id, "jobs"],
    queryFn: () => fetchCompanyWatchlistJobs(item.id, { limit: 50 }),
  });
  return (
    <div className="fixed inset-0 z-50 overflow-y-auto bg-[#101828]/40 px-4 py-6">
      <div className="ml-auto min-h-full max-w-4xl rounded-md bg-white p-5 shadow-xl">
        <div className="flex justify-between gap-4">
          <div>
            <h2 className="text-lg font-semibold text-[#171923]">Jobs at {item.company_name}</h2>
            <p className="mt-1 text-sm text-[#667085]">Related jobs from existing ScoutAI job data.</p>
          </div>
          <button type="button" onClick={onClose} className="h-fit rounded border border-[#c8ced8] px-3 py-1.5 text-sm">Close</button>
        </div>
        {jobsQuery.isLoading ? <p className="mt-4 text-sm text-[#667085]">Loading jobs...</p> : null}
        {jobsQuery.error ? <Notice tone="danger">Could not load related jobs.</Notice> : null}
        {jobsQuery.data?.jobs.length === 0 ? <p className="mt-4 rounded border border-dashed border-[#c8ced8] p-4 text-sm text-[#667085]">No jobs found for this watched company yet.</p> : null}
        <div className="mt-4 space-y-3">
          {(jobsQuery.data?.jobs ?? []).map((job) => <RelatedJobCard key={job.id} job={job} />)}
        </div>
      </div>
    </div>
  );
}

function RelatedJobCard({ job }: { job: CompanyWatchlistJob }) {
  const applyUrl = normalizeExternalUrl(job.apply_url) ?? normalizeExternalUrl(job.job_url);
  const source = sourceAttribution(job.job_url);
  return (
    <article className="rounded-md border border-[#d9dee8] p-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h3 className="font-semibold text-[#171923]">{job.title}</h3>
          <div className="mt-1 flex flex-wrap gap-2 text-sm text-[#667085]">
            <span>{source.label.replace("Source: ", "")}</span>
            <span>{formatMatchTier(job.match_tier)}</span>
            {job.total_score != null ? <span>Score {Math.round(job.total_score)}</span> : null}
            <span>{labelize(job.eligibility_status)}</span>
            <span>{formatDate(job.published_at)}</span>
          </div>
        </div>
        <div className="flex flex-wrap gap-2">
          <Link href={`/jobs/${job.id}/workspace`} className="rounded border border-[#c8ced8] px-3 py-2 text-sm font-medium text-[#344054]">Open Workspace</Link>
          {applyUrl ? <a href={applyUrl} target="_blank" rel="noopener noreferrer" className="rounded bg-[#172033] px-3 py-2 text-sm font-medium text-white">View Job / Apply</a> : null}
        </div>
      </div>
    </article>
  );
}

function passesFilters(item: CompanyWatchlistResponse, filters: { search: string; status: string; priority: string; remote: string; junior: string; tag: string; hasRecommended: boolean; needsReview: boolean }) {
  const query = filters.search.trim().toLowerCase();
  if (query && !`${item.company_name} ${item.company_domain ?? ""}`.toLowerCase().includes(query)) return false;
  if (filters.status && item.watch_status !== filters.status) return false;
  if (filters.priority && item.priority !== filters.priority) return false;
  if (filters.remote && item.remote_interest !== filters.remote) return false;
  if (filters.junior && item.junior_friendliness_signal !== filters.junior) return false;
  if (filters.tag && !(item.tags ?? []).some((tag) => tag.toLowerCase().includes(filters.tag.toLowerCase()))) return false;
  if (filters.hasRecommended && !(Number(item.recommended_job_count ?? 0) > 0)) return false;
  if (filters.needsReview && !needsReview(item)) return false;
  return true;
}

function sortItems(items: CompanyWatchlistResponse[], sort: string) {
  const priorityRank: Record<string, number> = { high: 3, medium: 2, low: 1 };
  return [...items].sort((a, b) => {
    if (sort === "company") return a.company_name.localeCompare(b.company_name);
    if (sort === "jobs") return Number(b.job_count ?? 0) - Number(a.job_count ?? 0);
    if (sort === "recommended") return Number(b.recommended_job_count ?? 0) - Number(a.recommended_job_count ?? 0);
    if (sort === "updated") return dateValue(b.updated_at ?? b.created_at) - dateValue(a.updated_at ?? a.created_at);
    return (priorityRank[b.priority] ?? 0) - (priorityRank[a.priority] ?? 0) || Number(b.recommended_job_count ?? 0) - Number(a.recommended_job_count ?? 0) || Number(needsReview(b)) - Number(needsReview(a)) || dateValue(b.updated_at ?? b.created_at) - dateValue(a.updated_at ?? a.created_at);
  });
}

function toPayload(form: Record<string, string>): CompanyWatchlistCreate {
  return {
    company_name: form.company_name || undefined,
    company_domain: form.company_domain || undefined,
    company_url: form.company_url || undefined,
    watch_status: form.watch_status,
    priority: form.priority,
    interest_reason: form.interest_reason || undefined,
    target_roles: splitList(form.target_roles),
    preferred_locations: splitList(form.preferred_locations),
    notes: form.notes || undefined,
    tags: splitList(form.tags),
    remote_interest: form.remote_interest,
    junior_friendliness_signal: form.junior_friendliness_signal,
  };
}

function splitList(value: string) {
  return value.split(",").map((item) => item.trim()).filter(Boolean);
}

function needsReview(item: CompanyWatchlistResponse) {
  if (item.priority === "high" && !item.last_reviewed_at) return true;
  if (Number(item.recommended_job_count ?? 0) > 0) return true;
  if (!item.last_reviewed_at) return false;
  return Date.now() - new Date(item.last_reviewed_at).getTime() > 14 * 24 * 60 * 60 * 1000;
}

function dateValue(value?: string | null) {
  return value ? new Date(value).getTime() || 0 : 0;
}

function formatDate(value?: string | null) {
  return value ? new Intl.DateTimeFormat("en", { dateStyle: "medium" }).format(new Date(value)) : "Not listed";
}

function Input({ label, value, onChange, placeholder }: { label: string; value: string; onChange: (value: string) => void; placeholder?: string }) {
  return (
    <label>
      <span className="mb-1 block text-xs font-medium uppercase tracking-normal text-[#667085]">{label}</span>
      <input value={value} placeholder={placeholder} onChange={(event) => onChange(event.target.value)} className="w-full rounded border border-[#c8ced8] px-3 py-2 text-sm" />
    </label>
  );
}

function Select({ label, value, options, onChange, includeAll = false }: { label: string; value: string; options: string[]; onChange: (value: string) => void; includeAll?: boolean }) {
  return (
    <label>
      <span className="mb-1 block text-xs font-medium uppercase tracking-normal text-[#667085]">{label}</span>
      <select value={value} onChange={(event) => onChange(event.target.value)} className="w-full rounded border border-[#c8ced8] px-3 py-2 text-sm">
        {includeAll ? <option value="">All</option> : null}
        {options.map((option) => <option key={option} value={option}>{labelize(option)}</option>)}
      </select>
    </label>
  );
}

function Checkbox({ label, checked, onChange }: { label: string; checked: boolean; onChange: (value: boolean) => void }) {
  return <label className="flex items-center gap-2"><input type="checkbox" checked={checked} onChange={(event) => onChange(event.target.checked)} className="h-4 w-4" />{label}</label>;
}

function Badge({ children }: { children: string }) {
  return <span className="rounded-full border border-[#d9dee8] bg-[#f8fafc] px-2 py-0.5 text-xs font-medium text-[#475467]">{children}</span>;
}

function Fact({ label, value }: { label: string; value: string }) {
  return <div><dt className="text-xs font-medium uppercase tracking-normal text-[#667085]">{label}</dt><dd className="mt-1 text-[#344054]">{value}</dd></div>;
}

function Notice({ tone, children }: { tone: "success" | "danger"; children: ReactNode }) {
  return <div className={`mb-4 rounded-md border p-3 text-sm ${tone === "success" ? "border-[#bbf7d0] bg-[#f0fdf4] text-[#166534]" : "border-[#fecaca] bg-[#fff7f7] text-[#991b1b]"}`}>{children}</div>;
}

function LoadingState() {
  return <div className="h-56 animate-pulse rounded-md border border-[#d9dee8] bg-white" />;
}
