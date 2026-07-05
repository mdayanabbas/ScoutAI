import type { CompanyPage } from "@/types/company-page";
import {
  EmptyState,
  formatDateTime,
  formatLabel,
  formatNumber,
  SectionError,
  SectionShell,
} from "@/components/companies/detail-format";

export function CompanyPages({
  pages,
  error,
}: {
  pages?: CompanyPage[];
  error?: Error | null;
}) {
  return (
    <SectionShell title="Pages">
      {error ? <SectionError message={error.message} /> : null}
      {!error && pages?.length === 0 ? (
        <EmptyState message="No company pages found." />
      ) : null}
      {!error && pages && pages.length > 0 ? (
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-[#edf0f5] text-left text-sm">
            <thead className="text-xs uppercase text-[#667085]">
              <tr>
                <th className="px-3 py-2 font-semibold">URL</th>
                <th className="px-3 py-2 font-semibold">Type</th>
                <th className="px-3 py-2 font-semibold">Title</th>
                <th className="px-3 py-2 font-semibold">Status</th>
                <th className="px-3 py-2 font-semibold">Length</th>
                <th className="px-3 py-2 font-semibold">Last Crawled</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#edf0f5]">
              {pages.map((page) => (
                <tr key={page.id}>
                  <td className="max-w-xs truncate px-3 py-3">
                    <a
                      href={page.url}
                      target="_blank"
                      rel="noreferrer"
                      className="text-[#175cd3] hover:underline"
                    >
                      {page.url}
                    </a>
                  </td>
                  <td className="whitespace-nowrap px-3 py-3 text-[#475467]">
                    {formatLabel(page.page_type)}
                  </td>
                  <td className="max-w-xs truncate px-3 py-3 text-[#475467]">
                    {page.title ?? "None"}
                  </td>
                  <td className="whitespace-nowrap px-3 py-3 text-[#475467]">
                    {page.status_code ?? "None"}
                  </td>
                  <td className="whitespace-nowrap px-3 py-3 text-[#475467]">
                    {formatNumber(page.content_length)}
                  </td>
                  <td className="whitespace-nowrap px-3 py-3 text-[#475467]">
                    {formatDateTime(page.last_crawled_at)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
    </SectionShell>
  );
}
