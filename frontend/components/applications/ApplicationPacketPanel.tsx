"use client";

import { useState } from "react";

import { ResumeGapAnalysis } from "@/components/applications/ResumeGapAnalysis";
import {
  formatMatchTier,
  formatRemoteEligibility,
  labelize,
} from "@/components/recommendations/recommendation-format";
import type {
  ApplicationPacketItem,
  ApplicationPacketResponse,
  ApplicationPacketSection,
} from "@/types/application-packet";

type CopyKey = "resume" | "cover" | "dm" | "plan";

export function ApplicationPacketPanel({
  packet,
}: {
  packet: ApplicationPacketResponse;
}) {
  const [copyMessage, setCopyMessage] = useState<string | null>(null);
  const resumeBullets = cleanItems(packet.resume_bullet_suggestions);
  const coverItems = cleanItems(packet.cover_note_outline?.items);
  const coldDmItems = cleanItems(packet.cold_dm_outline?.items);
  const applyPlan = cleanItems(packet.suggested_apply_plan);
  const risks = cleanItems(packet.risks_to_verify);

  async function copy(key: CopyKey, text: string) {
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
    <section className="mt-4 rounded-md border border-[#bbf7d0] bg-[#f0fdf4] p-4">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h3 className="text-sm font-semibold text-[#172033]">
            Application Packet
          </h3>
          <p className="mt-1 text-sm leading-6 text-[#344054]">
            {packet.application_positioning ?? "Application packet is ready."}
          </p>
        </div>
        <div className="flex flex-wrap gap-2 text-xs text-[#475467]">
          {packet.resume_used ? (
            <span className="rounded border border-[#bbf7d0] bg-white px-2 py-1 text-[#166534]">
              Resume-aware
            </span>
          ) : null}
          {packet.match_tier ? (
            <span className="rounded border border-[#bbf7d0] bg-white px-2 py-1">
              {formatMatchTier(packet.match_tier)}
            </span>
          ) : null}
          {packet.remote_eligibility ? (
            <span className="rounded border border-[#bbf7d0] bg-white px-2 py-1">
              {formatRemoteEligibility(packet.remote_eligibility)}
            </span>
          ) : null}
          {packet.total_score != null ? (
            <span className="rounded border border-[#bbf7d0] bg-white px-2 py-1">
              Score {Math.round(packet.total_score)}
            </span>
          ) : null}
        </div>
      </div>

      {copyMessage ? (
        <p className="mt-3 text-xs font-medium text-[#166534]">{copyMessage}</p>
      ) : null}

      <ResumeGapAnalysis
        resumeUsed={packet.resume_used}
        resumeMatchSummary={packet.resume_match_summary}
        resumeStrengths={packet.resume_strengths}
        resumeGaps={packet.resume_gaps}
        resumeBulletSources={packet.resume_bullet_sources}
      />

      <div className="mt-4 grid gap-3 lg:grid-cols-2">
        <PacketList title="Resume Focus" items={cleanItems(packet.resume_focus)} />
        <PacketList
          title="Risks To Verify"
          items={risks}
          emptyText="No major risks detected."
          tone="warning"
        />
      </div>

      {resumeBullets.length > 0 ? (
        <PacketList
          title="Resume Bullet Suggestions"
          items={resumeBullets}
          actionLabel="Copy resume bullets"
          onAction={() => copy("resume", formatItemsForCopy(resumeBullets))}
          className="mt-3"
        />
      ) : null}

      <div className="mt-3 grid gap-3 lg:grid-cols-2">
        <PacketList
          title="Project Evidence To Use"
          items={cleanItems(packet.project_evidence_to_use)}
        />
        <PacketList
          title="Application Checklist"
          items={cleanItems(packet.application_checklist)}
          asChecklist
        />
      </div>

      {applyPlan.length > 0 ? (
        <PacketList
          title="Suggested Apply Plan"
          items={applyPlan}
          ordered
          actionLabel="Copy apply plan"
          onAction={() => copy("plan", formatItemsForCopy(applyPlan, true))}
          className="mt-3"
        />
      ) : null}

      <div className="mt-3 grid gap-3 lg:grid-cols-2">
        <PacketOutline
          section={packet.cover_note_outline}
          fallbackTitle="Cover Note Outline"
          actionLabel="Copy cover note outline"
          onCopy={() => copy("cover", formatItemsForCopy(coverItems))}
        />
        <PacketOutline
          section={packet.cold_dm_outline}
          fallbackTitle="Cold DM Outline"
          actionLabel="Copy cold DM outline"
          onCopy={() => copy("dm", formatItemsForCopy(coldDmItems))}
        />
      </div>
    </section>
  );
}

function PacketOutline({
  section,
  fallbackTitle,
  actionLabel,
  onCopy,
}: {
  section?: ApplicationPacketSection | null;
  fallbackTitle: string;
  actionLabel: string;
  onCopy: () => void;
}) {
  const items = cleanItems(section?.items);
  if (items.length === 0) {
    return null;
  }
  return (
    <PacketList
      title={section?.title ?? fallbackTitle}
      items={items}
      actionLabel={actionLabel}
      onAction={onCopy}
    />
  );
}

function PacketList({
  title,
  items,
  emptyText = "None listed.",
  tone = "neutral",
  ordered = false,
  asChecklist = false,
  actionLabel,
  onAction,
  className = "",
}: {
  title: string;
  items: ApplicationPacketItem[];
  emptyText?: string;
  tone?: "neutral" | "warning";
  ordered?: boolean;
  asChecklist?: boolean;
  actionLabel?: string;
  onAction?: () => void;
  className?: string;
}) {
  const ListTag = ordered ? "ol" : "ul";
  return (
    <div
      className={[
        "rounded border bg-white p-3",
        tone === "warning" ? "border-[#fed7aa]" : "border-[#d9dee8]",
        className,
      ].join(" ")}
    >
      <div className="flex items-center justify-between gap-3">
        <h4 className="text-xs font-semibold uppercase tracking-normal text-[#667085]">
          {title}
        </h4>
        {actionLabel && onAction ? (
          <button
            type="button"
            onClick={onAction}
            className="rounded border border-[#c8ced8] px-2 py-1 text-xs font-medium text-[#344054] hover:bg-[#f8fafc]"
          >
            {actionLabel}
          </button>
        ) : null}
      </div>
      {items.length > 0 ? (
        <ListTag
          className={[
            "mt-2 space-y-2 text-sm text-[#344054]",
            ordered ? "list-decimal pl-5" : "",
          ].join(" ")}
        >
          {items.map((item, index) => (
            <li key={`${item.value ?? title}-${index}`} className={ordered ? "" : "flex gap-2"}>
              {asChecklist ? (
                <span
                  aria-hidden="true"
                  className="mt-1 h-3 w-3 shrink-0 rounded border border-[#98a2b3] bg-white"
                />
              ) : null}
              <span>
                {item.label && item.label !== title ? (
                  <span className="font-medium">{labelize(item.label)}: </span>
                ) : null}
                {item.value ?? item.label ?? "Packet item"}
                {item.reason ? (
                  <span className="block text-xs text-[#667085]">
                    {item.reason}
                  </span>
                ) : null}
              </span>
            </li>
          ))}
        </ListTag>
      ) : (
        <p className="mt-2 text-sm text-[#98a2b3]">{emptyText}</p>
      )}
    </div>
  );
}

function cleanItems(items?: ApplicationPacketItem[] | null) {
  return (items ?? []).filter((item) => Boolean(item?.value ?? item?.label));
}

function formatItemsForCopy(items: ApplicationPacketItem[], ordered = false) {
  return items
    .map((item, index) => {
      const prefix = ordered ? `${index + 1}. ` : "- ";
      const label = item.label ? `${labelize(item.label)}: ` : "";
      return `${prefix}${label}${item.value ?? ""}`;
    })
    .join("\n");
}
