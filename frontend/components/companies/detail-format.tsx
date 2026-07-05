import type { ReactNode } from "react";

export function formatDateTime(value: string | null | undefined) {
  if (!value) {
    return "None";
  }

  return new Intl.DateTimeFormat("en", {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit",
  }).format(new Date(value));
}

export function formatDate(value: string | null | undefined) {
  if (!value) {
    return "None";
  }

  return new Intl.DateTimeFormat("en", {
    month: "short",
    day: "numeric",
    year: "numeric",
  }).format(new Date(value));
}

export function formatLabel(value: string | null | undefined) {
  if (!value) {
    return "None";
  }

  return value
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

export function formatNumber(value: number | null | undefined) {
  return value === null || value === undefined ? "None" : value.toLocaleString();
}

export function SectionShell({
  title,
  children,
}: {
  title: string;
  children: ReactNode;
}) {
  return (
    <section className="rounded-md border border-[#d9dee8] bg-white shadow-sm">
      <div className="border-b border-[#edf0f5] px-4 py-3">
        <h2 className="text-base font-semibold text-[#171923]">{title}</h2>
      </div>
      <div className="p-4">{children}</div>
    </section>
  );
}

export function EmptyState({ message }: { message: string }) {
  return (
    <div className="rounded-md border border-dashed border-[#c8ced8] p-6 text-center text-sm text-[#667085]">
      {message}
    </div>
  );
}

export function SectionError({ message }: { message?: string }) {
  return (
    <div className="rounded-md border border-[#fecaca] bg-[#fff7f7] p-3 text-sm text-[#991b1b]">
      {message ?? "This section could not load."}
    </div>
  );
}

export function StatusBadge({ value }: { value: string }) {
  const positive =
    value === "active" || value === "success" || value === "running";
  const negative =
    value === "failed" || value === "inactive" || value === "expired";

  return (
    <span
      className={[
        "inline-flex rounded px-2 py-1 text-xs font-medium",
        positive
          ? "bg-[#dcfce7] text-[#166534]"
          : negative
            ? "bg-[#fee2e2] text-[#991b1b]"
            : "bg-[#eef2f6] text-[#475467]",
      ].join(" ")}
    >
      {formatLabel(value)}
    </span>
  );
}
