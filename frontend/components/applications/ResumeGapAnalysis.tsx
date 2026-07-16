"use client";

import Link from "next/link";

import { labelize } from "@/components/recommendations/recommendation-format";
import type { ApplicationPacketEvidenceItem } from "@/types/application-packet";

type NormalizedGapItem = {
  label?: string | null;
  value: string;
  reason?: string | null;
  severity?: string | null;
};

export function ResumeGapAnalysis({
  resumeUsed,
  resumeMatchSummary,
  resumeStrengths,
  resumeGaps,
  resumeBulletSources,
  compact = false,
}: {
  resumeUsed?: boolean | null;
  resumeMatchSummary?: string | null;
  resumeStrengths?: ApplicationPacketEvidenceItem[] | null;
  resumeGaps?: ApplicationPacketEvidenceItem[] | null;
  resumeBulletSources?: ApplicationPacketEvidenceItem[] | null;
  compact?: boolean;
}) {
  const strengths = normalizeItems(resumeStrengths);
  const gaps = normalizeItems(resumeGaps);
  const bulletSources = normalizeItems(resumeBulletSources);

  if (!resumeUsed) {
    return (
      <section className={panelClass(compact, "neutral")}>
        <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <h4 className="text-sm font-semibold text-[#172033]">
                Resume Gap Analysis
              </h4>
              <span className="rounded-full border border-[#d9dee8] bg-white px-2 py-0.5 text-xs font-medium text-[#667085]">
                No resume used
              </span>
            </div>
            <p className="mt-1 text-sm text-[#667085]">
              No active resume was used. Upload a resume to get accurate gap analysis.
            </p>
          </div>
          <Link
            href="/profile/resume"
            className="w-fit rounded bg-[#172033] px-3 py-2 text-sm font-medium text-white hover:bg-[#0f1728]"
          >
            Upload Resume
          </Link>
        </div>
      </section>
    );
  }

  return (
    <section className={panelClass(compact, "success")}>
      <div className="flex flex-wrap items-center gap-2">
        <h4 className="text-sm font-semibold text-[#172033]">
          Resume Gap Analysis
        </h4>
        <span className="rounded-full border border-[#bbf7d0] bg-white px-2 py-0.5 text-xs font-medium text-[#166534]">
          Resume-aware
        </span>
      </div>

      <p className="mt-2 text-sm leading-6 text-[#344054]">
        {resumeMatchSummary ?? "Uploaded resume evidence was used for this packet."}
      </p>

      {!compact ? (
        <>
          <div className="mt-3 grid gap-3 lg:grid-cols-2">
            <ItemGroup
              title="Strengths Found in Resume"
              items={strengths}
              emptyText="No clear resume strengths detected for this role. Review your resume parsing."
              tone="success"
            />
            <ItemGroup
              title="Gaps to Fix"
              items={gaps}
              emptyText="No major resume gaps detected."
              tone="warning"
              showFix
            />
          </div>
          {bulletSources.length > 0 ? (
            <ItemGroup
              title="Bullet Sources"
              items={bulletSources}
              emptyText="No resume-backed bullet sources detected."
              className="mt-3"
            />
          ) : null}
        </>
      ) : (
        <div className="mt-3 flex flex-wrap gap-2 text-xs">
          <span className="rounded border border-[#bbf7d0] bg-white px-2 py-1 text-[#166534]">
            {strengths.length} strengths
          </span>
          <span className="rounded border border-[#fed7aa] bg-white px-2 py-1 text-[#9a3412]">
            {gaps.length} gaps
          </span>
        </div>
      )}
    </section>
  );
}

function ItemGroup({
  title,
  items,
  emptyText,
  tone = "neutral",
  showFix = false,
  className = "",
}: {
  title: string;
  items: NormalizedGapItem[];
  emptyText: string;
  tone?: "neutral" | "success" | "warning";
  showFix?: boolean;
  className?: string;
}) {
  return (
    <div
      className={[
        "rounded border bg-white p-3",
        tone === "success" ? "border-[#bbf7d0]" : tone === "warning" ? "border-[#fed7aa]" : "border-[#d9dee8]",
        className,
      ].join(" ")}
    >
      <h5 className="text-xs font-semibold uppercase tracking-normal text-[#667085]">
        {title}
      </h5>
      {items.length > 0 ? (
        <ul className="mt-2 space-y-2 text-sm text-[#344054]">
          {items.map((item, index) => (
            <li key={`${title}-${item.value}-${index}`}>
              <div className="flex flex-wrap items-center gap-2">
                <span>{item.value}</span>
                {tone === "warning" ? (
                  <span className="rounded-full border border-[#fed7aa] bg-[#fff7ed] px-2 py-0.5 text-xs text-[#9a3412]">
                    {severityLabel(item.severity)}
                  </span>
                ) : null}
              </div>
              {item.reason ? (
                <span className="block text-xs text-[#667085]">{item.reason}</span>
              ) : null}
              {showFix ? (
                <span className="block text-xs text-[#667085]">
                  {suggestedFix(item)}
                </span>
              ) : null}
            </li>
          ))}
        </ul>
      ) : (
        <p className="mt-2 text-sm text-[#98a2b3]">{emptyText}</p>
      )}
    </div>
  );
}

export function normalizeResumeGapItems(items?: ApplicationPacketEvidenceItem[] | null) {
  return normalizeItems(items);
}

function normalizeItems(items?: ApplicationPacketEvidenceItem[] | null): NormalizedGapItem[] {
  return (items ?? [])
    .map((item) => {
      if (typeof item === "string") {
        return { value: item };
      }
      if (item && typeof item === "object") {
        const record = item as Record<string, unknown>;
        const value = record.value ?? record.title ?? record.name ?? record.label ?? record.text;
        return {
          label: stringOrNull(record.label),
          value: typeof value === "string" ? value : value ? JSON.stringify(value) : "",
          reason: stringOrNull(record.reason),
          severity: stringOrNull(record.severity ?? record.gap_severity ?? record.type),
        };
      }
      return { value: "" };
    })
    .filter((item) => item.value.trim());
}

function severityLabel(value?: string | null) {
  const normalized = value?.toLowerCase().replaceAll("_", " ");
  if (normalized === "missing") {
    return "Missing";
  }
  if (normalized === "weak evidence") {
    return "Weak evidence";
  }
  if (normalized === "needs clarification") {
    return "Needs clarification";
  }
  if (normalized === "optional improvement") {
    return "Optional improvement";
  }
  return "Needs review";
}

function suggestedFix(item: NormalizedGapItem) {
  const text = `${item.value} ${item.reason ?? ""}`.toLowerCase();
  if (text.includes("project")) {
    return "Move relevant project higher or mention in a project bullet if true.";
  }
  if (text.includes("skill") || text.includes("docker") || text.includes("fastapi") || text.includes("python")) {
    return "Add proof to your technical skills section if true.";
  }
  if (text.includes("remote") || text.includes("collaboration")) {
    return "Add proof of async or remote collaboration if true.";
  }
  return "Verify before applying and add proof if true.";
}

function panelClass(compact: boolean, tone: "neutral" | "success") {
  return [
    "rounded border p-3",
    compact ? "" : "mt-4",
    tone === "success" ? "border-[#bbf7d0] bg-white" : "border-[#d9dee8] bg-white",
  ].join(" ");
}

function stringOrNull(value: unknown) {
  return typeof value === "string" && value.trim() ? value : null;
}
