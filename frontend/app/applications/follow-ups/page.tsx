"use client";

import Link from "next/link";
import { useMemo, useState } from "react";

import { PageHeader } from "@/components/layout/PageHeader";
import { APP_ROUTES } from "@/lib/app-routes";
import {
  applicationFollowUpStorage,
  buildFollowUpDashboard,
  dueDateState,
  needsAction,
  outreachStatusOptions,
  outreachTypeOptions,
  type ApplicationFollowUpItem,
  type ApplicationOutreachStatus,
  type ApplicationOutreachType,
} from "@/lib/application-follow-ups";

type Tab = "needs_action" | "due_today" | "overdue" | "upcoming" | "sent" | "responded" | "closed" | "all";
type Sort = "due_soonest" | "overdue_first" | "last_action" | "company" | "status";

const tabs: Array<{ value: Tab; label: string }> = [
  { value: "needs_action", label: "Needs Action" },
  { value: "due_today", label: "Due Today" },
  { value: "overdue", label: "Overdue" },
  { value: "upcoming", label: "Upcoming" },
  { value: "sent", label: "Sent" },
  { value: "responded", label: "Responded" },
  { value: "closed", label: "Closed" },
  { value: "all", label: "All" },
];

export default function ApplicationFollowUpsPage() {
  const [items, setItems] = useState<ApplicationFollowUpItem[]>(() => applicationFollowUpStorage.getFollowUps());
  const [tab, setTab] = useState<Tab>("needs_action");
  const [statusFilter, setStatusFilter] = useState("all");
  const [typeFilter, setTypeFilter] = useState("all");
  const [search, setSearch] = useState("");
  const [sort, setSort] = useState<Sort>("overdue_first");
  const [editing, setEditing] = useState<ApplicationFollowUpItem | null>(null);
  const [creating, setCreating] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const dashboard = useMemo(() => buildFollowUpDashboard(items), [items]);
  const visibleItems = useMemo(
    () => sortItems(items.filter((item) => matches(item, { tab, statusFilter, typeFilter, search })), sort),
    [items, search, sort, statusFilter, tab, typeFilter],
  );

  function refresh(note?: string) {
    setItems(applicationFollowUpStorage.getFollowUps());
    if (note) setMessage(note);
  }

  function updateItem(id: string, changes: Partial<ApplicationFollowUpItem>, note: string) {
    const result = applicationFollowUpStorage.updateFollowUp(id, changes);
    refresh(result.ok ? note : result.error ?? "Could not update follow-up.");
  }

  function deleteItem(id: string) {
    if (!window.confirm("Delete this follow-up item?")) return;
    const result = applicationFollowUpStorage.deleteFollowUp(id);
    refresh(result.ok ? "Deleted follow-up." : result.error ?? "Could not delete follow-up.");
  }

  function saveManual(values: FollowUpFormValues) {
    const result = values.id
      ? applicationFollowUpStorage.updateFollowUp(values.id, values)
      : applicationFollowUpStorage.saveFollowUp({
          job_id: values.job_id || `manual-${Date.now()}`,
          company_name: values.company_name,
          job_title: values.job_title,
          outreach_type: values.outreach_type,
          outreach_status: values.outreach_status,
          message_target: values.message_target,
          sent_at: valueToIso(values.sent_at),
          follow_up_due_at: valueToIso(values.follow_up_due_at),
          notes: values.notes,
          workspace_url: values.job_id ? `/jobs/${values.job_id}/workspace` : null,
        });
    setCreating(false);
    setEditing(null);
    refresh(result.ok ? "Saved follow-up." : result.error ?? "Could not save follow-up.");
  }

  return (
    <>
      <PageHeader
        title="Application Follow-up Tracker"
        description="Track manually sent outreach and follow-ups across your job search."
        actions={
          <div className="flex flex-wrap gap-2">
            <Link href={APP_ROUTES.discovery} className="rounded border border-[#c8ced8] bg-white px-3 py-2 text-sm font-medium text-[#344054] hover:bg-[#f8fafc]">Discovery Control</Link>
            <Link href={APP_ROUTES.commandCenter} className="rounded border border-[#c8ced8] bg-white px-3 py-2 text-sm font-medium text-[#344054] hover:bg-[#f8fafc]">Command Center</Link>
            <Link href={APP_ROUTES.analytics} className="rounded border border-[#c8ced8] bg-white px-3 py-2 text-sm font-medium text-[#344054] hover:bg-[#f8fafc]">Analytics</Link>
            <Link href={APP_ROUTES.pipeline} className="rounded border border-[#c8ced8] bg-white px-3 py-2 text-sm font-medium text-[#344054] hover:bg-[#f8fafc]">Pipeline</Link>
            <button type="button" onClick={() => setCreating(true)} className="rounded bg-[#172033] px-3 py-2 text-sm font-medium text-white hover:bg-[#0f1728]">Add Manual Follow-up</button>
          </div>
        }
      />

      {message ? <div className="mb-4 rounded border border-[#d9dee8] bg-white px-4 py-3 text-sm text-[#344054]">{message}</div> : null}

      <section className="mb-5 grid gap-3 sm:grid-cols-2 xl:grid-cols-7">
        <Metric label="Total follow-ups" value={dashboard.total} />
        <Metric label="Needs action" value={dashboard.needsAction} />
        <Metric label="Due today" value={dashboard.dueToday} />
        <Metric label="Overdue" value={dashboard.overdue} tone={dashboard.overdue ? "danger" : "default"} />
        <Metric label="Sent manually" value={dashboard.sentManually} />
        <Metric label="Responded" value={dashboard.responded} />
        <Metric label="Closed" value={dashboard.closed} />
      </section>

      <section className="mb-5 rounded-md border border-[#d9dee8] bg-white p-4">
        <div className="flex flex-wrap gap-2">
          {tabs.map((item) => (
            <button
              key={item.value}
              type="button"
              onClick={() => setTab(item.value)}
              className={`rounded px-3 py-2 text-sm font-medium ${tab === item.value ? "bg-[#172033] text-white" : "border border-[#c8ced8] text-[#344054] hover:bg-[#f8fafc]"}`}
            >
              {item.label}
            </button>
          ))}
        </div>
        <div className="mt-4 grid gap-3 lg:grid-cols-4">
          <input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search company, title, notes" className="rounded border border-[#c8ced8] px-3 py-2 text-sm" />
          <select value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)} className="rounded border border-[#c8ced8] px-3 py-2 text-sm">
            <option value="all">All statuses</option>
            {outreachStatusOptions.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
          </select>
          <select value={typeFilter} onChange={(event) => setTypeFilter(event.target.value)} className="rounded border border-[#c8ced8] px-3 py-2 text-sm">
            <option value="all">All outreach types</option>
            {outreachTypeOptions.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
          </select>
          <select value={sort} onChange={(event) => setSort(event.target.value as Sort)} className="rounded border border-[#c8ced8] px-3 py-2 text-sm">
            <option value="overdue_first">Overdue first</option>
            <option value="due_soonest">Follow-up due soonest</option>
            <option value="last_action">Last action</option>
            <option value="company">Company</option>
            <option value="status">Status</option>
          </select>
        </div>
      </section>

      {!items.length ? (
        <EmptyState text="No outreach follow-ups tracked yet. Create one from a cold DM draft or add a manual follow-up." />
      ) : !visibleItems.length ? (
        <EmptyState text={tab === "due_today" || tab === "overdue" ? "No follow-ups due right now." : "You are caught up on outreach follow-ups."} />
      ) : (
        <div className="grid gap-4">
          {visibleItems.map((item) => (
            <ApplicationFollowUpCard
              key={item.id}
              item={item}
              onEdit={() => setEditing(item)}
              onDelete={() => deleteItem(item.id)}
              onMarkSent={() => updateItem(item.id, { outreach_status: "sent_manually", sent_at: new Date().toISOString(), follow_up_due_at: addDaysIso(3) }, "Marked as manually sent.")}
              onMarkFollowUpSent={() => updateItem(item.id, { outreach_status: "follow_up_sent", follow_up_sent_at: new Date().toISOString() }, "Marked follow-up sent.")}
              onMarkResponded={() => updateItem(item.id, { outreach_status: "responded" }, "Marked responded.")}
              onMarkNoResponse={() => updateItem(item.id, { outreach_status: "no_response" }, "Marked no response.")}
              onClose={() => updateItem(item.id, { outreach_status: "closed" }, "Closed follow-up.")}
            />
          ))}
        </div>
      )}

      {creating || editing ? (
        <FollowUpForm
          item={editing}
          onCancel={() => {
            setCreating(false);
            setEditing(null);
          }}
          onSave={saveManual}
        />
      ) : null}
    </>
  );
}

function ApplicationFollowUpCard({
  item,
  onEdit,
  onDelete,
  onMarkSent,
  onMarkFollowUpSent,
  onMarkResponded,
  onMarkNoResponse,
  onClose,
}: {
  item: ApplicationFollowUpItem;
  onEdit: () => void;
  onDelete: () => void;
  onMarkSent: () => void;
  onMarkFollowUpSent: () => void;
  onMarkResponded: () => void;
  onMarkNoResponse: () => void;
  onClose: () => void;
}) {
  const dueState = dueDateState(item);
  return (
    <article className="rounded-md border border-[#d9dee8] bg-white p-4">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <div className="flex flex-wrap gap-2 text-xs text-[#475467]">
            <Badge>{labelize(item.outreach_type)}</Badge>
            <Badge>{labelize(item.outreach_status)}</Badge>
            {dueState === "overdue" ? <Badge tone="danger">Overdue follow-up</Badge> : null}
            {dueState === "due_today" ? <Badge tone="warning">Follow-up due</Badge> : null}
            {item.decision_status ? <Badge>{labelize(item.decision_status)}</Badge> : null}
          </div>
          <h2 className="mt-3 text-base font-semibold text-[#171923]">{item.job_title || "Untitled job"}</h2>
          <p className="mt-1 text-sm text-[#667085]">{item.company_name || "Unknown company"}</p>
          {item.draft_preview ? <p className="mt-3 text-sm leading-6 text-[#344054]">{item.draft_preview}</p> : null}
          <dl className="mt-3 grid gap-3 text-sm sm:grid-cols-2 xl:grid-cols-4">
            <Fact label="Target" value={item.message_target || "Not set"} />
            <Fact label="Sent" value={formatDate(item.sent_at)} />
            <Fact label="Due" value={formatDate(item.follow_up_due_at)} />
            <Fact label="Last action" value={formatDate(item.last_action_at)} />
          </dl>
          {item.notes ? <p className="mt-3 text-sm text-[#475467]"><span className="font-medium">Notes:</span> {item.notes}</p> : null}
        </div>
        <div className="flex shrink-0 flex-wrap gap-2 lg:justify-end">
          <Link href={`/discovery/control-center#review-queue`} className="rounded border border-[#c8ced8] px-3 py-2 text-sm font-medium text-[#344054] hover:bg-[#f8fafc]">Open Action Center</Link>
          {item.workspace_url ? <Link href={item.workspace_url} className="rounded bg-[#172033] px-3 py-2 text-sm font-medium text-white hover:bg-[#0f1728]">Open Workspace</Link> : null}
          {item.job_url ? <a href={item.job_url} target="_blank" rel="noopener noreferrer" className="rounded border border-[#c8ced8] px-3 py-2 text-sm font-medium text-[#344054] hover:bg-[#f8fafc]">Open Job</a> : null}
          <button type="button" onClick={onMarkSent} className="rounded border border-[#c8ced8] px-3 py-2 text-sm font-medium text-[#344054] hover:bg-[#f8fafc]">Mark Sent Manually</button>
          <button type="button" onClick={onMarkFollowUpSent} className="rounded border border-[#c8ced8] px-3 py-2 text-sm font-medium text-[#344054] hover:bg-[#f8fafc]">Mark Follow-up Sent</button>
          <button type="button" onClick={onMarkResponded} className="rounded border border-[#c8ced8] px-3 py-2 text-sm font-medium text-[#344054] hover:bg-[#f8fafc]">Responded</button>
          <button type="button" onClick={onMarkNoResponse} className="rounded border border-[#c8ced8] px-3 py-2 text-sm font-medium text-[#344054] hover:bg-[#f8fafc]">No Response</button>
          <button type="button" onClick={onClose} className="rounded border border-[#c8ced8] px-3 py-2 text-sm font-medium text-[#344054] hover:bg-[#f8fafc]">Close</button>
          <button type="button" onClick={onEdit} className="rounded border border-[#c8ced8] px-3 py-2 text-sm font-medium text-[#344054] hover:bg-[#f8fafc]">Edit Notes</button>
          <button type="button" onClick={onDelete} className="rounded border border-[#fecaca] px-3 py-2 text-sm font-medium text-[#991b1b] hover:bg-[#fff7f7]">Delete</button>
        </div>
      </div>
    </article>
  );
}

type FollowUpFormValues = {
  id?: string;
  job_id: string;
  company_name?: string | null;
  job_title?: string | null;
  outreach_type: ApplicationOutreachType;
  outreach_status: ApplicationOutreachStatus;
  message_target?: string | null;
  sent_at?: string | null;
  follow_up_due_at?: string | null;
  notes?: string | null;
};

function FollowUpForm({ item, onCancel, onSave }: { item: ApplicationFollowUpItem | null; onCancel: () => void; onSave: (values: FollowUpFormValues) => void }) {
  const [values, setValues] = useState<FollowUpFormValues>({
    id: item?.id,
    job_id: item?.job_id ?? "",
    company_name: item?.company_name ?? "",
    job_title: item?.job_title ?? "",
    outreach_type: item?.outreach_type ?? "other",
    outreach_status: item?.outreach_status ?? "drafted",
    message_target: item?.message_target ?? "",
    sent_at: isoToInput(item?.sent_at),
    follow_up_due_at: isoToInput(item?.follow_up_due_at),
    notes: item?.notes ?? "",
  });
  const canSave = Boolean(values.job_id || values.job_title);
  return (
    <div className="fixed inset-0 z-50 bg-[#101828]/30 p-4">
      <div className="mx-auto max-w-2xl rounded-md bg-white p-5 shadow-xl">
        <div className="mb-4 flex items-start justify-between gap-3">
          <div>
            <h2 className="text-lg font-semibold text-[#171923]">{item ? "Edit Follow-up" : "Add Manual Follow-up"}</h2>
            <p className="mt-1 text-sm text-[#667085]">ScoutAI only tracks manual outreach. It will not send anything.</p>
          </div>
          <button type="button" onClick={onCancel} className="rounded border border-[#c8ced8] px-3 py-2 text-sm text-[#344054]">Close</button>
        </div>
        <div className="grid gap-3 md:grid-cols-2">
          <Input label="Job ID" value={values.job_id} onChange={(value) => setValues((current) => ({ ...current, job_id: value }))} />
          <Input label="Job title" value={values.job_title ?? ""} onChange={(value) => setValues((current) => ({ ...current, job_title: value }))} />
          <Input label="Company" value={values.company_name ?? ""} onChange={(value) => setValues((current) => ({ ...current, company_name: value }))} />
          <Input label="Message target" value={values.message_target ?? ""} onChange={(value) => setValues((current) => ({ ...current, message_target: value }))} />
          <label className="text-sm font-medium text-[#344054]">Outreach type<select value={values.outreach_type} onChange={(event) => setValues((current) => ({ ...current, outreach_type: event.target.value as ApplicationOutreachType }))} className="mt-1 w-full rounded border border-[#c8ced8] px-3 py-2 text-sm">{outreachTypeOptions.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}</select></label>
          <label className="text-sm font-medium text-[#344054]">Status<select value={values.outreach_status} onChange={(event) => setValues((current) => ({ ...current, outreach_status: event.target.value as ApplicationOutreachStatus }))} className="mt-1 w-full rounded border border-[#c8ced8] px-3 py-2 text-sm">{outreachStatusOptions.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}</select></label>
          <Input label="Sent date" type="datetime-local" value={values.sent_at ?? ""} onChange={(value) => setValues((current) => ({ ...current, sent_at: value }))} />
          <Input label="Follow-up due date" type="datetime-local" value={values.follow_up_due_at ?? ""} onChange={(value) => setValues((current) => ({ ...current, follow_up_due_at: value }))} />
          <label className="text-sm font-medium text-[#344054] md:col-span-2">Notes<textarea value={values.notes ?? ""} onChange={(event) => setValues((current) => ({ ...current, notes: event.target.value }))} rows={4} className="mt-1 w-full rounded border border-[#c8ced8] px-3 py-2 text-sm" /></label>
        </div>
        {!canSave ? <p className="mt-3 text-sm text-[#991b1b]">Job title or job ID is required.</p> : null}
        <div className="mt-5 flex justify-end gap-2">
          <button type="button" onClick={onCancel} className="rounded border border-[#c8ced8] px-3 py-2 text-sm font-medium text-[#344054]">Cancel</button>
          <button type="button" disabled={!canSave} onClick={() => onSave(values)} className="rounded bg-[#172033] px-3 py-2 text-sm font-medium text-white disabled:opacity-60">Save Follow-up</button>
        </div>
      </div>
    </div>
  );
}

function matches(item: ApplicationFollowUpItem, filters: { tab: Tab; statusFilter: string; typeFilter: string; search: string }) {
  if (filters.statusFilter !== "all" && item.outreach_status !== filters.statusFilter) return false;
  if (filters.typeFilter !== "all" && item.outreach_type !== filters.typeFilter) return false;
  const term = filters.search.trim().toLowerCase();
  if (term) {
    const haystack = [item.company_name, item.job_title, item.notes, item.draft_preview, item.decision_status].join(" ").toLowerCase();
    if (!haystack.includes(term)) return false;
  }
  const due = dueDateState(item);
  if (filters.tab === "needs_action") return needsAction(item);
  if (filters.tab === "due_today") return due === "due_today";
  if (filters.tab === "overdue") return due === "overdue";
  if (filters.tab === "upcoming") return due === "upcoming";
  if (filters.tab === "sent") return item.outreach_status === "sent_manually" || item.outreach_status === "follow_up_sent";
  if (filters.tab === "responded") return item.outreach_status === "responded";
  if (filters.tab === "closed") return item.outreach_status === "closed";
  return true;
}

function sortItems(items: ApplicationFollowUpItem[], sort: Sort) {
  const cloned = [...items];
  if (sort === "company") return cloned.sort((a, b) => String(a.company_name ?? "").localeCompare(String(b.company_name ?? "")));
  if (sort === "status") return cloned.sort((a, b) => a.outreach_status.localeCompare(b.outreach_status));
  if (sort === "last_action") return cloned.sort((a, b) => dateValue(b.last_action_at) - dateValue(a.last_action_at));
  if (sort === "due_soonest") return cloned.sort((a, b) => dateValue(a.follow_up_due_at, Number.MAX_SAFE_INTEGER) - dateValue(b.follow_up_due_at, Number.MAX_SAFE_INTEGER));
  return cloned.sort((a, b) => dueRank(a) - dueRank(b) || dateValue(a.follow_up_due_at, Number.MAX_SAFE_INTEGER) - dateValue(b.follow_up_due_at, Number.MAX_SAFE_INTEGER));
}

function dueRank(item: ApplicationFollowUpItem) {
  const state = dueDateState(item);
  if (state === "overdue") return 0;
  if (state === "due_today") return 1;
  if (state === "upcoming") return 2;
  return 3;
}

function Metric({ label, value, tone = "default" }: { label: string; value: number; tone?: "default" | "danger" }) {
  return <div className={`rounded border p-3 ${tone === "danger" ? "border-[#fecaca] bg-[#fff7f7]" : "border-[#e4e7ec] bg-white"}`}><p className="text-xs font-medium uppercase tracking-normal text-[#667085]">{label}</p><p className="mt-1 text-xl font-semibold text-[#171923]">{value}</p></div>;
}

function EmptyState({ text }: { text: string }) {
  return <div className="rounded-md border border-[#d9dee8] bg-white p-5 text-sm text-[#667085]">{text}</div>;
}

function Badge({ children, tone = "default" }: { children: string; tone?: "default" | "danger" | "warning" }) {
  const color = tone === "danger" ? "border-[#fecaca] bg-[#fff7f7] text-[#991b1b]" : tone === "warning" ? "border-[#fed7aa] bg-[#fff7ed] text-[#9a3412]" : "border-[#e4e7ec] bg-[#fcfcfd] text-[#475467]";
  return <span className={`rounded border px-2 py-1 ${color}`}>{children}</span>;
}

function Fact({ label, value }: { label: string; value: string }) {
  return <div><dt className="text-xs font-medium uppercase tracking-normal text-[#667085]">{label}</dt><dd className="mt-1 text-[#344054]">{value}</dd></div>;
}

function Input({ label, value, onChange, type = "text" }: { label: string; value: string; onChange: (value: string) => void; type?: string }) {
  return <label className="text-sm font-medium text-[#344054]">{label}<input type={type} value={value} onChange={(event) => onChange(event.target.value)} className="mt-1 w-full rounded border border-[#c8ced8] px-3 py-2 text-sm" /></label>;
}

function labelize(value?: string | null) {
  return (value ?? "unknown").replace(/_/g, " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function formatDate(value?: string | null) {
  if (!value) return "Not set";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? "Invalid date" : date.toLocaleString();
}

function dateValue(value?: string | null, fallback = 0) {
  if (!value) return fallback;
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? fallback : date.getTime();
}

function addDaysIso(days: number) {
  const date = new Date();
  date.setDate(date.getDate() + days);
  return date.toISOString();
}

function valueToIso(value?: string | null) {
  if (!value) return null;
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? null : date.toISOString();
}

function isoToInput(value?: string | null) {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  const offset = date.getTimezoneOffset() * 60000;
  return new Date(date.getTime() - offset).toISOString().slice(0, 16);
}
