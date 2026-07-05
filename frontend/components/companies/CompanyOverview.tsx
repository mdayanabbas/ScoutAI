import type { Company } from "@/types/company";
import {
  formatDate,
  formatLabel,
  formatNumber,
  SectionShell,
  StatusBadge,
} from "@/components/companies/detail-format";

function Field({ label, value }: { label: string; value: string | number }) {
  return (
    <div>
      <dt className="text-xs font-medium uppercase text-[#667085]">{label}</dt>
      <dd className="mt-1 text-sm text-[#171923]">{value}</dd>
    </div>
  );
}

export function CompanyOverview({ company }: { company: Company }) {
  const employeeRange =
    company.employee_count_min || company.employee_count_max
      ? `${formatNumber(company.employee_count_min)} - ${formatNumber(
          company.employee_count_max,
        )}`
      : "None";

  return (
    <SectionShell title="Overview">
      <div className="space-y-5">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <h2 className="text-xl font-semibold text-[#171923]">
              {company.name}
            </h2>
            <a
              href={company.website_url}
              target="_blank"
              rel="noreferrer"
              className="mt-1 inline-block text-sm font-medium text-[#175cd3] hover:underline"
            >
              {company.website_url}
            </a>
          </div>
          <StatusBadge value={company.is_active ? "active" : "inactive"} />
        </div>

        {company.description ? (
          <p className="text-sm leading-6 text-[#475467]">
            {company.description}
          </p>
        ) : null}

        <dl className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <Field label="Domain" value={company.normalized_domain} />
          <Field label="Stage" value={formatLabel(company.stage)} />
          <Field label="Source" value={formatLabel(company.source)} />
          <Field label="Country" value={company.country ?? "None"} />
          <Field label="City" value={company.city ?? "None"} />
          <Field label="Employees" value={employeeRange} />
          <Field
            label="Founded"
            value={company.founded_year?.toString() ?? "None"}
          />
          <Field label="Created" value={formatDate(company.created_at)} />
        </dl>
      </div>
    </SectionShell>
  );
}
