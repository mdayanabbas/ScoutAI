"use client";

import { CompanyTable } from "@/components/companies/CompanyTable";
import { PageHeader } from "@/components/layout/PageHeader";
import { useCompanies } from "@/hooks/use-companies";

function LoadingState() {
  return (
    <div className="rounded-md border border-[#d9dee8] bg-white p-4 shadow-sm">
      <div className="space-y-3">
        {Array.from({ length: 8 }).map((_, index) => (
          <div
            key={index}
            className="h-10 animate-pulse rounded bg-[#eef2f6]"
          />
        ))}
      </div>
    </div>
  );
}

export default function CompaniesPage() {
  const params = { page: 1, page_size: 20 };
  const { data, isLoading, isError, error, refetch } = useCompanies(params);

  return (
    <>
      <PageHeader
        title="Companies"
        description="Browse the companies currently tracked in ScoutAI."
      />

      {isLoading ? <LoadingState /> : null}

      {isError ? (
        <div className="rounded-md border border-[#fecaca] bg-[#fff7f7] p-4">
          <h2 className="text-sm font-semibold text-[#991b1b]">
            Companies could not load
          </h2>
          <p className="mt-1 text-sm text-[#7f1d1d]">
            {error instanceof Error ? error.message : "Check the backend API."}
          </p>
          <button
            type="button"
            onClick={() => refetch()}
            className="mt-4 rounded bg-[#172033] px-3 py-2 text-sm font-medium text-white"
          >
            Retry
          </button>
        </div>
      ) : null}

      {data && data.items.length === 0 ? (
        <div className="rounded-md border border-dashed border-[#c8ced8] bg-white p-8 text-center">
          <h2 className="text-base font-semibold text-[#171923]">
            No companies yet
          </h2>
          <p className="mt-2 text-sm text-[#667085]">
            Companies created through the backend API will show up here.
          </p>
        </div>
      ) : null}

      {data && data.items.length > 0 ? (
        <div className="space-y-3">
          <div className="text-sm text-[#667085]">
            Showing {data.items.length} of {data.total} companies
          </div>
          <CompanyTable companies={data.items} />
        </div>
      ) : null}
    </>
  );
}
