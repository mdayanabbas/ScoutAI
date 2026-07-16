"use client";

import Link from "next/link";
import { useState } from "react";
import type { ReactNode } from "react";

import { labelize } from "@/components/recommendations/recommendation-format";
import type {
  ResumeBulletSuggestion,
  ResumeImprovementItem,
  ResumeImprovementResponse,
  ResumeSectionSuggestion,
  ResumeSkillGapSuggestion,
} from "@/types/resume-improvement";

type CopyKey = "sections" | "bullets" | "gaps" | "next";

export function ResumeImprovementPanel({
  improvement,
}: {
  improvement: ResumeImprovementResponse;
}) {
  const [copyMessage, setCopyMessage] = useState<string | null>(null);
  const sections = improvement.section_suggestions ?? [];
  const bullets = improvement.bullet_suggestions ?? [];
  const gaps = improvement.skill_gap_suggestions ?? [];
  const projects = improvement.project_reordering_suggestions ?? [];
  const remoteFit = improvement.remote_fit_suggestions ?? [];
  const risks = improvement.risks ?? [];

  async function copy(_key: CopyKey, text: string) {
    if (!text.trim()) {
      return;
    }
    try {
      await navigator.clipboard.writeText(text);
      setCopyMessage("Copied.");
      window.setTimeout(() => setCopyMessage(null), 1800);
    } catch {
      setCopyMessage("Copy failed.");
    }
  }

  return (
    <section className="mt-4 rounded-md border border-[#bfdbfe] bg-[#eff6ff] p-4">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <h3 className="text-sm font-semibold text-[#172033]">
              Resume Improvement Suggestions
            </h3>
            <span
              className={[
                "rounded-full border bg-white px-2 py-0.5 text-xs font-medium",
                improvement.resume_used
                  ? "border-[#bbf7d0] text-[#166534]"
                  : "border-[#fed7aa] text-[#9a3412]",
              ].join(" ")}
            >
              {improvement.resume_used ? "Resume-aware" : "No active resume used"}
            </span>
          </div>
          <p className="mt-2 text-sm leading-6 text-[#344054]">
            {improvement.improvement_summary ?? "Resume suggestions are ready."}
          </p>
        </div>
        {!improvement.resume_used ? (
          <Link
            href="/profile/resume"
            className="w-fit rounded bg-[#172033] px-3 py-2 text-sm font-medium text-white hover:bg-[#0f1728]"
          >
            Upload Resume
          </Link>
        ) : null}
      </div>

      {!improvement.resume_used ? (
        <p className="mt-3 rounded border border-[#fed7aa] bg-white px-3 py-2 text-sm text-[#9a3412]">
          Upload and activate a resume for accurate improvement suggestions.
        </p>
      ) : null}

      {copyMessage ? (
        <p className="mt-3 text-xs font-medium text-[#1d4ed8]">{copyMessage}</p>
      ) : null}

      {improvement.suggested_next_action ? (
        <div className="mt-4 rounded border border-[#93c5fd] bg-white p-3">
          <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <h4 className="text-xs font-semibold uppercase tracking-normal text-[#1d4ed8]">
                Suggested Next Action
              </h4>
              <p className="mt-1 text-sm text-[#172033]">
                {improvement.suggested_next_action}
              </p>
            </div>
            <button
              type="button"
              onClick={() => copy("next", improvement.suggested_next_action ?? "")}
              className="w-fit rounded border border-[#c8ced8] px-2 py-1 text-xs font-medium text-[#344054] hover:bg-[#f8fafc]"
            >
              Copy next action
            </button>
          </div>
        </div>
      ) : null}

      <SuggestionSection
        title="Section Suggestions"
        emptyText="No section-specific suggestions available."
        actionLabel="Copy section suggestions"
        onCopy={() => copy("sections", formatSectionSuggestions(sections))}
      >
        <SectionSuggestions items={sections} />
      </SuggestionSection>

      <SuggestionSection
        title="Resume Bullet Suggestions"
        emptyText="No bullet suggestions generated."
        actionLabel="Copy bullets"
        onCopy={() => copy("bullets", bullets.map((item) => item.bullet_template ?? "").filter(Boolean).join("\n"))}
      >
        <BulletSuggestions items={bullets} />
      </SuggestionSection>

      <SuggestionSection
        title="Skill Gap Suggestions"
        emptyText="No major skill gaps detected."
        actionLabel="Copy skill gaps"
        onCopy={() => copy("gaps", formatSkillGaps(gaps))}
      >
        <SkillGapSuggestions items={gaps} />
      </SuggestionSection>

      <ItemList
        title="Project Reordering Suggestions"
        items={projects}
        emptyText="No clear projects detected in resume. Add or clarify projects before applying."
      />

      {remoteFit.length > 0 ? (
        <ItemList title="Remote Fit Suggestions" items={remoteFit} />
      ) : null}

      <ItemList
        title="Risks"
        items={risks}
        emptyText="No major resume risks detected."
        tone="warning"
      />
    </section>
  );
}

function SuggestionSection({
  title,
  emptyText,
  actionLabel,
  onCopy,
  children,
}: {
  title: string;
  emptyText: string;
  actionLabel: string;
  onCopy: () => void;
  children: ReactNode;
}) {
  const hasContent = Boolean(children);
  return (
    <div className="mt-3 rounded border border-[#d9dee8] bg-white p-3">
      <div className="flex items-center justify-between gap-3">
        <h4 className="text-xs font-semibold uppercase tracking-normal text-[#667085]">
          {title}
        </h4>
        {hasContent ? (
          <button
            type="button"
            onClick={onCopy}
            className="rounded border border-[#c8ced8] px-2 py-1 text-xs font-medium text-[#344054] hover:bg-[#f8fafc]"
          >
            {actionLabel}
          </button>
        ) : null}
      </div>
      {hasContent ? children : <p className="mt-2 text-sm text-[#98a2b3]">{emptyText}</p>}
    </div>
  );
}

function SectionSuggestions({ items }: { items: ResumeSectionSuggestion[] }) {
  if (items.length === 0) {
    return null;
  }
  const groups = groupBy(items, (item) => item.section ?? "Other");
  return (
    <div className="mt-2 grid gap-3 lg:grid-cols-2">
      {Object.entries(groups).map(([section, sectionItems]) => (
        <div key={section} className="rounded border border-[#edf0f5] bg-[#fcfcfd] p-3">
          <h5 className="text-sm font-semibold text-[#171923]">{labelize(section)}</h5>
          <ul className="mt-2 space-y-2 text-sm text-[#344054]">
            {sectionItems.map((item, index) => (
              <li key={`${section}-${index}`}>
                <div className="flex flex-wrap items-center gap-2">
                  <span>{item.suggestion ?? "Review this section."}</span>
                  <PriorityBadge value={item.priority} />
                </div>
                <span className="block text-xs text-[#667085]">
                  {labelize(item.action)} - {item.reason}
                </span>
              </li>
            ))}
          </ul>
        </div>
      ))}
    </div>
  );
}

function BulletSuggestions({ items }: { items: ResumeBulletSuggestion[] }) {
  if (items.length === 0) {
    return null;
  }
  return (
    <ul className="mt-2 space-y-3 text-sm text-[#344054]">
      {items.map((item, index) => (
        <li key={`${item.target_section ?? "bullet"}-${index}`} className="rounded border border-[#edf0f5] bg-[#fcfcfd] p-3">
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-xs font-semibold uppercase tracking-normal text-[#667085]">
              {item.target_section ?? "Resume"}
            </span>
            <span
              className={[
                "rounded-full border bg-white px-2 py-0.5 text-xs font-medium",
                item.supported_by_resume
                  ? "border-[#bbf7d0] text-[#166534]"
                  : "border-[#fed7aa] text-[#9a3412]",
              ].join(" ")}
            >
              {item.supported_by_resume ? "Supported by resume" : "Verify first"}
            </span>
          </div>
          <p className="mt-2">{item.bullet_template ?? "Bullet template unavailable."}</p>
          {item.supporting_evidence ? (
            <p className="mt-1 text-xs text-[#667085]">Evidence: {item.supporting_evidence}</p>
          ) : null}
          {item.caution ? (
            <p className="mt-1 text-xs text-[#9a3412]">{item.caution}</p>
          ) : null}
        </li>
      ))}
    </ul>
  );
}

function SkillGapSuggestions({ items }: { items: ResumeSkillGapSuggestion[] }) {
  if (items.length === 0) {
    return null;
  }
  return (
    <div className="mt-2 grid gap-2">
      {items.map((item, index) => (
        <div key={`${item.skill ?? "skill"}-${index}`} className="rounded border border-[#edf0f5] bg-[#fcfcfd] p-3 text-sm">
          <div className="flex flex-wrap items-center gap-2">
            <span className="font-medium text-[#171923]">{item.skill ?? "Skill"}</span>
            <span
              className={[
                "rounded-full border bg-white px-2 py-0.5 text-xs",
                item.found_in_resume
                  ? "border-[#bbf7d0] text-[#166534]"
                  : "border-[#fed7aa] text-[#9a3412]",
              ].join(" ")}
            >
              {item.found_in_resume ? "Found" : "Missing"}
            </span>
            <span className="rounded-full border border-[#d9dee8] bg-white px-2 py-0.5 text-xs text-[#475467]">
              {sourceLabel(item.required_or_preferred)}
            </span>
          </div>
          <p className="mt-2 text-[#344054]">{item.suggestion}</p>
          {item.caution ? <p className="mt-1 text-xs text-[#9a3412]">{item.caution}</p> : null}
        </div>
      ))}
    </div>
  );
}

function ItemList({
  title,
  items,
  emptyText = "None listed.",
  tone = "neutral",
}: {
  title: string;
  items: ResumeImprovementItem[];
  emptyText?: string;
  tone?: "neutral" | "warning";
}) {
  return (
    <div className={["mt-3 rounded border bg-white p-3", tone === "warning" ? "border-[#fed7aa]" : "border-[#d9dee8]"].join(" ")}>
      <h4 className="text-xs font-semibold uppercase tracking-normal text-[#667085]">
        {title}
      </h4>
      {items.length > 0 ? (
        <ul className="mt-2 space-y-2 text-sm text-[#344054]">
          {items.map((item, index) => (
            <li key={`${title}-${index}`}>
              <div className="flex flex-wrap items-center gap-2">
                <span>{item.suggestion ?? "Review item."}</span>
                <PriorityBadge value={item.priority} />
              </div>
              {item.reason ? <span className="block text-xs text-[#667085]">{item.reason}</span> : null}
              {item.evidence ? <span className="block text-xs text-[#667085]">Evidence: {item.evidence}</span> : null}
              {item.caution ? <span className="block text-xs text-[#9a3412]">{item.caution}</span> : null}
            </li>
          ))}
        </ul>
      ) : (
        <p className="mt-2 text-sm text-[#98a2b3]">{emptyText}</p>
      )}
    </div>
  );
}

function PriorityBadge({ value }: { value?: string | null }) {
  const normalized = value ?? "medium";
  const classes =
    normalized === "high"
      ? "border-[#fecaca] text-[#991b1b]"
      : normalized === "low"
        ? "border-[#d9dee8] text-[#475467]"
        : "border-[#fed7aa] text-[#9a3412]";
  return (
    <span className={`rounded-full border bg-white px-2 py-0.5 text-xs font-medium ${classes}`}>
      {labelize(normalized)}
    </span>
  );
}

function groupBy<T>(items: T[], keyFn: (item: T) => string) {
  return items.reduce<Record<string, T[]>>((acc, item) => {
    const key = keyFn(item);
    acc[key] = [...(acc[key] ?? []), item];
    return acc;
  }, {});
}

function formatSectionSuggestions(items: ResumeSectionSuggestion[]) {
  return items
    .map((item) => `- ${item.section ?? "Section"}: ${item.suggestion ?? ""}`)
    .join("\n");
}

function formatSkillGaps(items: ResumeSkillGapSuggestion[]) {
  return items
    .map((item) => `- ${item.skill ?? "Skill"} (${sourceLabel(item.required_or_preferred)}): ${item.suggestion ?? ""}`)
    .join("\n");
}

function sourceLabel(value?: string | null) {
  if (value === "required") {
    return "Required";
  }
  if (value === "preferred") {
    return "Preferred";
  }
  if (value === "inferred") {
    return "Inferred";
  }
  return labelize(value);
}
