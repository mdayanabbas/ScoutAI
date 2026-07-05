import type { Company } from "@/types/company";

export function CompanyCard({ company }: { company: Company }) {
  return (
    <article className="rounded-md border border-[#d9dee8] bg-white p-4 shadow-sm">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h2 className="text-sm font-semibold text-[#171923]">
            {company.name}
          </h2>
          <p className="mt-1 text-sm text-[#667085]">
            {company.normalized_domain}
          </p>
        </div>
        <span className="rounded bg-[#eef2f6] px-2 py-1 text-xs font-medium text-[#475467]">
          {company.is_active ? "Active" : "Inactive"}
        </span>
      </div>
      {company.description ? (
        <p className="mt-3 line-clamp-3 text-sm leading-6 text-[#475467]">
          {company.description}
        </p>
      ) : null}
    </article>
  );
}
