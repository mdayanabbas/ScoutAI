import type { RecentActivityItem } from "@/types/dashboard";

function formatDate(value: string) {
  return new Intl.DateTimeFormat("en", {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  }).format(new Date(value));
}

function typeLabel(type: string) {
  return type
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

export function RecentActivity({
  items,
}: {
  items: RecentActivityItem[];
}) {
  if (items.length === 0) {
    return (
      <section className="rounded-md border border-dashed border-[#c8ced8] bg-white p-8 text-center">
        <h2 className="text-base font-semibold text-[#171923]">
          No recent activity
        </h2>
        <p className="mt-2 text-sm text-[#667085]">
          New companies, jobs, crawl runs, and agent runs will appear here.
        </p>
      </section>
    );
  }

  return (
    <section className="rounded-md border border-[#d9dee8] bg-white shadow-sm">
      <div className="border-b border-[#d9dee8] px-4 py-3">
        <h2 className="text-base font-semibold text-[#171923]">
          Recent Activity
        </h2>
      </div>
      <ul className="divide-y divide-[#edf0f5]">
        {items.map((item) => (
          <li
            key={`${item.type}-${item.entity_id}-${item.created_at}`}
            className="flex flex-col gap-2 px-4 py-4 sm:flex-row sm:items-start sm:justify-between"
          >
            <div className="min-w-0">
              <div className="flex flex-wrap items-center gap-2">
                <span className="rounded bg-[#eef2f6] px-2 py-1 text-xs font-medium text-[#475467]">
                  {typeLabel(item.type)}
                </span>
                <p className="text-sm font-medium text-[#171923]">
                  {item.title}
                </p>
              </div>
              {item.description ? (
                <p className="mt-1 text-sm text-[#667085]">
                  {item.description}
                </p>
              ) : null}
            </div>
            <time className="shrink-0 text-sm text-[#667085]">
              {formatDate(item.created_at)}
            </time>
          </li>
        ))}
      </ul>
    </section>
  );
}
