"use client";

import { useState } from "react";

import { CompanyForm } from "@/components/companies/CompanyForm";
import { CompanyTable } from "@/components/companies/CompanyTable";
import { PageHeader } from "@/components/layout/PageHeader";
import { useCompanies, useCreateCompany } from "@/hooks/use-companies";
import type { CompanyCreateInput } from "@/types/company";

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
  const createCompany = useCreateCompany();
  const [isCreateOpen, setIsCreateOpen] = useState(false);

  function openCreate() {
    createCompany.reset();
    setIsCreateOpen(true);
  }

  function closeCreate() {
    createCompany.reset();
    setIsCreateOpen(false);
  }

  async function handleCreateCompany(input: CompanyCreateInput) {
    await createCompany.mutateAsync(input);
    closeCreate();
  }

  return (
    <>
      <PageHeader
        title="Companies"
        description="Browse the companies currently tracked in ScoutAI."
        actions={
          <button
            type="button"
            onClick={openCreate}
            className="rounded bg-[#172033] px-4 py-2 text-sm font-medium text-white hover:bg-[#24314a]"
          >
            Add Company
          </button>
        }
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
            Add your first company to start building the ScoutAI workspace.
          </p>
          <button
            type="button"
            onClick={openCreate}
            className="mt-5 rounded bg-[#172033] px-4 py-2 text-sm font-medium text-white hover:bg-[#24314a]"
          >
            Add Company
          </button>
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

      {isCreateOpen ? (
        <div className="fixed inset-0 z-50 overflow-y-auto bg-[#101828]/40 px-4 py-6 sm:py-10">
          <div className="mx-auto max-w-3xl rounded-md bg-white shadow-xl">
            <div className="flex items-start justify-between gap-4 border-b border-[#edf0f5] px-5 py-4">
              <div>
                <h2 className="text-lg font-semibold text-[#171923]">
                  Add Company
                </h2>
                <p className="mt-1 text-sm text-[#667085]">
                  Create a company record connected to the backend API.
                </p>
              </div>
              <button
                type="button"
                onClick={closeCreate}
                className="rounded border border-[#c8ced8] px-2.5 py-1.5 text-sm text-[#475467] hover:bg-[#f8fafc]"
              >
                Close
              </button>
            </div>
            <div className="px-5 py-5">
              <CompanyForm
                isSubmitting={createCompany.isPending}
                submitError={createCompany.error}
                onSubmit={handleCreateCompany}
                onCancel={closeCreate}
              />
            </div>
          </div>
        </div>
      ) : null}
    </>
  );
}
