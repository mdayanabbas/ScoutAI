import type { UserProfile } from "@/types/profile";

function formatLabel(value: string | null | undefined) {
  if (!value) {
    return "Unknown";
  }
  return value
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function formatDate(value: string | null | undefined) {
  if (!value) {
    return "Never";
  }
  return new Intl.DateTimeFormat("en", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function count(values: string[] | null | undefined) {
  return values?.length ?? 0;
}

export function ProfileSummary({ profile }: { profile: UserProfile }) {
  return (
    <aside className="rounded-md border border-[#d9dee8] bg-white p-4">
      <h2 className="text-base font-semibold text-[#171923]">
        {profile.display_name ?? "Unnamed Profile"}
      </h2>
      <p className="mt-1 text-sm text-[#667085]">
        {profile.years_experience ?? 0} years experience
      </p>
      <dl className="mt-4 space-y-3 text-sm">
        <SummaryItem label="Target Roles" value={count(profile.target_roles)} />
        <SummaryItem label="Skills" value={count(profile.skills)} />
        <SummaryItem
          label="Remote"
          value={formatLabel(profile.remote_preference)}
        />
        <SummaryItem
          label="Preferred Stages"
          value={
            profile.preferred_company_stages?.length
              ? profile.preferred_company_stages.map(formatLabel).join(", ")
              : "None"
          }
        />
        <SummaryItem
          label="Last Updated"
          value={formatDate(profile.updated_at ?? profile.created_at)}
        />
      </dl>
    </aside>
  );
}

function SummaryItem({ label, value }: { label: string; value: string | number }) {
  return (
    <div>
      <dt className="text-xs font-medium uppercase text-[#667085]">{label}</dt>
      <dd className="mt-1 text-[#171923]">{value}</dd>
    </div>
  );
}
