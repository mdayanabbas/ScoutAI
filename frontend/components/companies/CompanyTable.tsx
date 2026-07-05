import Link from "next/link";

import type { Company } from "@/types/company";

function formatDate(value: string) {
  return new Intl.DateTimeFormat("en", {
    month: "short",
    day: "numeric",
    year: "numeric",
  }).format(new Date(value));
}

function formatValue(value: string | null | undefined) {
  if (!value) {
    return "None";
  }

  return value
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function StatusBadge({ active }: { active: boolean }) {
  return (
    <span
      className={[
        "inline-flex rounded px-2 py-1 text-xs font-medium",
        active
          ? "bg-[#dcfce7] text-[#166534]"
          : "bg-[#f2f4f7] text-[#475467]",
      ].join(" ")}
    >
      {active ? "Active" : "Inactive"}
    </span>
  );
}

export function CompanyTable({
  companies,
  onEdit,
  onDelete,
  deletingCompanyId,
}: {
  companies: Company[];
  onEdit?: (company: Company) => void;
  onDelete?: (company: Company) => void;
  deletingCompanyId?: string | null;
}) {
  const showActions = Boolean(onEdit || onDelete);

  return (
    <div className="overflow-hidden rounded-md border border-[#d9dee8] bg-white shadow-sm">
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-[#edf0f5] text-left text-sm">
          <thead className="bg-[#f8fafc] text-xs uppercase text-[#667085]">
            <tr>
              <th className="px-4 py-3 font-semibold">Name</th>
              <th className="px-4 py-3 font-semibold">Domain</th>
              <th className="px-4 py-3 font-semibold">Stage</th>
              <th className="px-4 py-3 font-semibold">Source</th>
              <th className="px-4 py-3 font-semibold">Country</th>
              <th className="px-4 py-3 font-semibold">Status</th>
              <th className="px-4 py-3 font-semibold">Created</th>
              {showActions ? (
                <th className="px-4 py-3 text-right font-semibold">Actions</th>
              ) : null}
            </tr>
          </thead>
          <tbody className="divide-y divide-[#edf0f5]">
            {companies.map((company) => (
              <tr key={company.id} className="hover:bg-[#f8fafc]">
                <td className="whitespace-nowrap px-4 py-4 font-medium text-[#171923]">
                  <Link
                    href={`/companies/${company.id}`}
                    className="text-[#175cd3] hover:underline"
                  >
                    {company.name}
                  </Link>
                </td>
                <td className="whitespace-nowrap px-4 py-4 text-[#475467]">
                  {company.normalized_domain}
                </td>
                <td className="whitespace-nowrap px-4 py-4 text-[#475467]">
                  {formatValue(company.stage)}
                </td>
                <td className="whitespace-nowrap px-4 py-4 text-[#475467]">
                  {formatValue(company.source)}
                </td>
                <td className="whitespace-nowrap px-4 py-4 text-[#475467]">
                  {company.country ?? "None"}
                </td>
                <td className="whitespace-nowrap px-4 py-4">
                  <StatusBadge active={company.is_active} />
                </td>
                <td className="whitespace-nowrap px-4 py-4 text-[#475467]">
                  {formatDate(company.created_at)}
                </td>
                {showActions ? (
                  <td className="whitespace-nowrap px-4 py-4 text-right">
                    <div className="flex justify-end gap-2">
                      {onEdit ? (
                        <button
                          type="button"
                          onClick={() => onEdit(company)}
                          className="rounded border border-[#c8ced8] bg-white px-2.5 py-1.5 text-xs font-medium text-[#344054] hover:bg-[#f8fafc]"
                        >
                          Edit
                        </button>
                      ) : null}
                      {onDelete ? (
                        <button
                          type="button"
                          onClick={() => onDelete(company)}
                          disabled={deletingCompanyId === company.id}
                          className="rounded border border-[#fca5a5] bg-white px-2.5 py-1.5 text-xs font-medium text-[#b42318] hover:bg-[#fff7f7] disabled:cursor-not-allowed disabled:opacity-60"
                        >
                          {deletingCompanyId === company.id ? "Deleting..." : "Delete"}
                        </button>
                      ) : null}
                    </div>
                  </td>
                ) : null}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
