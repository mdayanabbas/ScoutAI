import type { ReactNode } from "react";

export function StatusBadge({ value, children }: { value?: string | null; children?: ReactNode }) {
  const label = children ?? labelize(value);
  return <span className={`rounded border px-2 py-1 text-xs font-medium ${toneFor(value)}`}>{label}</span>;
}

export function labelize(value?: string | null) {
  return (value ?? "unknown").replace(/_/g, " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function toneFor(value?: string | null) {
  const normalized = String(value ?? "").toLowerCase();
  if (["failed", "error", "rejected", "skipped", "not_interested", "dismissed", "unsuitable", "archived", "no_response"].includes(normalized)) {
    return "border-[#fecaca] bg-[#fff7f7] text-[#991b1b]";
  }
  if (["partial", "stretch", "uncertain", "needs_custom_resume", "needs_cold_dm", "follow_up_due", "copied", "drafted"].includes(normalized)) {
    return "border-[#fed7aa] bg-[#fff7ed] text-[#9a3412]";
  }
  if (["succeeded", "success", "eligible", "best_match", "strong_match", "applied", "interviewing", "offer", "responded", "closed", "sent_manually", "follow_up_sent", "interested", "saved"].includes(normalized)) {
    return "border-[#bbf7d0] bg-[#f0fdf4] text-[#166534]";
  }
  return "border-[#e4e7ec] bg-white text-[#475467]";
}
