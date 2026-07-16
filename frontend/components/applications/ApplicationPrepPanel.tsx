import {
  formatMatchTier,
  formatRemoteEligibility,
  labelize,
} from "@/components/recommendations/recommendation-format";
import type {
  ApplicationPrepListItem,
  ApplicationPrepResponse,
} from "@/types/application-prep";

export function ApplicationPrepPanel({
  prep,
  compact = false,
}: {
  prep: ApplicationPrepResponse;
  compact?: boolean;
}) {
  return (
    <section className="mt-4 rounded-md border border-[#bfdbfe] bg-[#eff6ff] p-4">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h3 className="text-sm font-semibold text-[#172033]">
            Application Prep
          </h3>
          <p className="mt-1 text-sm leading-6 text-[#344054]">
            {prep.fit_summary ?? "Prep notes are ready."}
          </p>
        </div>
        <div className="flex flex-wrap gap-2 text-xs text-[#475467]">
          {prep.match_tier ? (
            <span className="rounded border border-[#bfdbfe] bg-white px-2 py-1">
              {formatMatchTier(prep.match_tier)}
            </span>
          ) : null}
          {prep.remote_eligibility ? (
            <span className="rounded border border-[#bfdbfe] bg-white px-2 py-1">
              {formatRemoteEligibility(prep.remote_eligibility)}
            </span>
          ) : null}
          {prep.total_score != null ? (
            <span className="rounded border border-[#bfdbfe] bg-white px-2 py-1">
              Score {Math.round(prep.total_score)}
            </span>
          ) : null}
        </div>
      </div>

      {prep.suggested_next_action ? (
        <div className="mt-3 rounded border border-[#93c5fd] bg-white px-3 py-2">
          <div className="text-xs font-medium uppercase tracking-normal text-[#1d4ed8]">
            Next Action
          </div>
          <p className="mt-1 text-sm text-[#172033]">
            {prep.suggested_next_action}
          </p>
        </div>
      ) : null}

      {!compact ? (
        <>
          <div className="mt-4 grid gap-3 lg:grid-cols-2">
            <PrepList title="Resume Focus" items={prep.resume_focus_points ?? []} />
            <PrepList title="Talking Points" items={prep.project_talking_points ?? []} />
            <PrepList
              title="Concerns"
              items={prep.concerns ?? []}
              emptyText="No major concerns detected."
            />
            <PrepList title="Checklist" items={prep.application_checklist ?? []} />
          </div>

          {(prep.missing_information ?? []).length > 0 ? (
            <div className="mt-4">
              <div className="text-xs font-medium uppercase tracking-normal text-[#667085]">
                Missing Info
              </div>
              <div className="mt-2 flex flex-wrap gap-2">
                {(prep.missing_information ?? []).map((item) => (
                  <span
                    key={item}
                    className="rounded border border-[#fed7aa] bg-[#fff7ed] px-2 py-1 text-xs text-[#9a3412]"
                  >
                    {labelize(item)}
                  </span>
                ))}
              </div>
            </div>
          ) : null}

          {prep.cold_dm_angle ? (
            <div className="mt-4 rounded border border-[#d9dee8] bg-white px-3 py-2">
              <div className="text-xs font-medium uppercase tracking-normal text-[#667085]">
                Cold DM Angle
              </div>
              <p className="mt-1 text-sm leading-6 text-[#344054]">
                {prep.cold_dm_angle}
              </p>
            </div>
          ) : null}
        </>
      ) : null}
    </section>
  );
}

function PrepList({
  title,
  items,
  emptyText = "None listed.",
}: {
  title: string;
  items: ApplicationPrepListItem[];
  emptyText?: string;
}) {
  return (
    <div className="rounded border border-[#d9dee8] bg-white p-3">
      <h4 className="text-xs font-semibold uppercase tracking-normal text-[#667085]">
        {title}
      </h4>
      {items.length > 0 ? (
        <ul className="mt-2 space-y-2 text-sm text-[#344054]">
          {items.map((item, index) => (
            <li key={`${item.value ?? title}-${index}`}>
              <span>{item.value ?? item.label ?? "Prep item"}</span>
              {item.reason ? (
                <span className="block text-xs text-[#667085]">{item.reason}</span>
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
