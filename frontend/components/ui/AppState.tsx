import Link from "next/link";
import type { ReactNode } from "react";

type Action = {
  label: string;
  href?: string;
  onClick?: () => void;
};

export function LoadingState({ message = "Loading ScoutAI..." }: { message?: string }) {
  return (
    <div className="rounded-md border border-[#d9dee8] bg-white p-5 text-sm text-[#667085]">
      <div className="flex items-center gap-3">
        <span className="h-2.5 w-2.5 animate-pulse rounded-full bg-[#175cd3]" />
        <span>{message}</span>
      </div>
    </div>
  );
}

export function ErrorState({
  title,
  message,
  onRetry,
  action,
}: {
  title: string;
  message?: string;
  onRetry?: () => void;
  action?: Action;
}) {
  return (
    <div className="rounded-md border border-[#fecaca] bg-[#fff7f7] p-5">
      <h2 className="text-sm font-semibold text-[#991b1b]">{title}</h2>
      {message ? <p className="mt-1 text-sm text-[#b42318]">{message}</p> : null}
      <ActionButtonRow className="mt-3">
        {onRetry ? <button type="button" onClick={onRetry} className={buttonClass("primary")}>Retry</button> : null}
        {action ? <StateAction action={action} /> : null}
      </ActionButtonRow>
    </div>
  );
}

export function EmptyState({
  title,
  message,
  action,
}: {
  title: string;
  message?: string;
  action?: Action;
}) {
  return (
    <div className="rounded-md border border-dashed border-[#c8ced8] bg-white p-8 text-center">
      <h2 className="text-base font-semibold text-[#171923]">{title}</h2>
      {message ? <p className="mx-auto mt-2 max-w-2xl text-sm text-[#667085]">{message}</p> : null}
      {action ? <div className="mt-4"><StateAction action={action} primary /></div> : null}
    </div>
  );
}

export function PartialDataWarning({ messages }: { messages: string[] }) {
  if (!messages.length) return null;
  return (
    <div className="mb-4 rounded-md border border-[#fed7aa] bg-[#fff7ed] px-4 py-3 text-sm text-[#9a3412]">
      {`Partial data shown: ${messages.join(" ")}`}
    </div>
  );
}

export function SectionCard({ children, className = "" }: { children: ReactNode; className?: string }) {
  return <section className={`rounded-md border border-[#d9dee8] bg-white p-5 ${className}`}>{children}</section>;
}

export function MetricCard({
  label,
  value,
  helper,
  tone = "default",
}: {
  label: string;
  value: string | number;
  helper?: string;
  tone?: "default" | "danger" | "warning" | "success";
}) {
  return (
    <div className={`rounded border p-3 ${metricTone(tone)}`}>
      <p className="text-xs font-medium uppercase tracking-normal text-[#667085]">{label}</p>
      <p className="mt-1 text-xl font-semibold text-[#171923]">{value}</p>
      {helper ? <p className="mt-1 text-xs text-[#667085]">{helper}</p> : null}
    </div>
  );
}

export function ActionButtonRow({ children, className = "" }: { children: ReactNode; className?: string }) {
  return <div className={`flex flex-wrap gap-2 ${className}`}>{children}</div>;
}

function StateAction({ action, primary = false }: { action: Action; primary?: boolean }) {
  if (action.href) return <Link href={action.href} className={buttonClass(primary ? "primary" : "secondary")}>{action.label}</Link>;
  return <button type="button" onClick={action.onClick} className={buttonClass(primary ? "primary" : "secondary")}>{action.label}</button>;
}

function buttonClass(tone: "primary" | "secondary") {
  return tone === "primary"
    ? "rounded bg-[#172033] px-3 py-2 text-sm font-medium text-white hover:bg-[#0f1728]"
    : "rounded border border-[#c8ced8] bg-white px-3 py-2 text-sm font-medium text-[#344054] hover:bg-[#f8fafc]";
}

function metricTone(tone: "default" | "danger" | "warning" | "success") {
  if (tone === "danger") return "border-[#fecaca] bg-[#fff7f7]";
  if (tone === "warning") return "border-[#fed7aa] bg-[#fff7ed]";
  if (tone === "success") return "border-[#bbf7d0] bg-[#f0fdf4]";
  return "border-[#e4e7ec] bg-white";
}
