import type { TechStackItem } from "@/types/tech-stack";
import {
  EmptyState,
  formatLabel,
  SectionError,
  SectionShell,
} from "@/components/companies/detail-format";

export function CompanyTechStack({
  items,
  error,
}: {
  items?: TechStackItem[];
  error?: Error | null;
}) {
  return (
    <SectionShell title="Tech Stack">
      {error ? <SectionError message={error.message} /> : null}
      {!error && items?.length === 0 ? (
        <EmptyState message="No tech stack items found." />
      ) : null}
      {!error && items && items.length > 0 ? (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {items.map((item) => (
            <article
              key={item.id}
              className="rounded-md border border-[#edf0f5] p-4"
            >
              <h3 className="text-sm font-semibold text-[#171923]">
                {item.name}
              </h3>
              <p className="mt-1 text-sm text-[#667085]">
                {formatLabel(item.category)} · {item.source ?? "Unknown source"}
              </p>
              <p className="mt-3 text-sm text-[#475467]">
                Confidence: {Math.round(item.confidence * 100)}%
              </p>
            </article>
          ))}
        </div>
      ) : null}
    </SectionShell>
  );
}
