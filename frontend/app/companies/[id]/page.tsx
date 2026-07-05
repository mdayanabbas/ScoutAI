"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useState } from "react";

import { CompanyAgentRuns } from "@/components/companies/CompanyAgentRuns";
import { CompanyCrawlRuns } from "@/components/companies/CompanyCrawlRuns";
import { CompanyForm } from "@/components/companies/CompanyForm";
import { CompanyJobs } from "@/components/companies/CompanyJobs";
import { CompanyOverview } from "@/components/companies/CompanyOverview";
import { CompanyPages } from "@/components/companies/CompanyPages";
import { CompanyTechStack } from "@/components/companies/CompanyTechStack";
import { PageHeader } from "@/components/layout/PageHeader";
import { ApiError } from "@/lib/api";
import { useCompanyAgentRuns } from "@/hooks/use-agent-runs";
import {
  useCompany,
  useDeleteCompany,
  useUpdateCompany,
} from "@/hooks/use-companies";
import { useCompanyPages } from "@/hooks/use-company-pages";
import { useCompanyCrawlRuns } from "@/hooks/use-crawl-runs";
import { useCompanyJobs } from "@/hooks/use-jobs";
import { useCompanyTechStack } from "@/hooks/use-tech-stack";
import type { CompanyUpdateInput } from "@/types/company";

function LoadingState() {
  return (
    <div className="space-y-4">
      {Array.from({ length: 5 }).map((_, index) => (
        <div
          key={index}
          className="h-40 animate-pulse rounded-md border border-[#d9dee8] bg-white"
        />
      ))}
    </div>
  );
}

function PageError({
  title,
  message,
  onRetry,
}: {
  title: string;
  message: string;
  onRetry?: () => void;
}) {
  return (
    <div className="rounded-md border border-[#fecaca] bg-[#fff7f7] p-4">
      <h2 className="text-sm font-semibold text-[#991b1b]">{title}</h2>
      <p className="mt-1 text-sm text-[#7f1d1d]">{message}</p>
      <div className="mt-4 flex flex-wrap gap-3">
        <Link
          href="/companies"
          className="rounded border border-[#c8ced8] bg-white px-3 py-2 text-sm font-medium text-[#344054] hover:bg-[#f8fafc]"
        >
          Back to Companies
        </Link>
        {onRetry ? (
          <button
            type="button"
            onClick={onRetry}
            className="rounded bg-[#172033] px-3 py-2 text-sm font-medium text-white"
          >
            Retry
          </button>
        ) : null}
      </div>
    </div>
  );
}

export default function CompanyDetailPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const companyId = params.id;
  const companyQuery = useCompany(companyId);
  const updateCompany = useUpdateCompany();
  const deleteCompany = useDeleteCompany();
  const pagesQuery = useCompanyPages(companyId);
  const jobsQuery = useCompanyJobs(companyId);
  const techStackQuery = useCompanyTechStack(companyId);
  const crawlRunsQuery = useCompanyCrawlRuns(companyId);
  const agentRunsQuery = useCompanyAgentRuns(companyId);

  const isNotFound =
    companyQuery.error instanceof ApiError && companyQuery.error.status === 404;
  const [isEditOpen, setIsEditOpen] = useState(false);
  const [isDeleteOpen, setIsDeleteOpen] = useState(false);

  function openEdit() {
    updateCompany.reset();
    setIsEditOpen(true);
  }

  function closeEdit() {
    updateCompany.reset();
    setIsEditOpen(false);
  }

  async function handleUpdateCompany(input: CompanyUpdateInput) {
    await updateCompany.mutateAsync({
      id: companyId,
      data: input,
    });
    await companyQuery.refetch();
    closeEdit();
  }

  function openDelete() {
    deleteCompany.reset();
    setIsDeleteOpen(true);
  }

  function closeDelete() {
    deleteCompany.reset();
    setIsDeleteOpen(false);
  }

  async function handleDeleteCompany() {
    await deleteCompany.mutateAsync(companyId);
    router.push("/companies");
  }

  return (
    <>
      <PageHeader
        title="Company Detail"
        description="Read-only company profile and related ScoutAI activity."
        actions={
          <>
            <Link
              href="/companies"
              className="rounded border border-[#c8ced8] bg-white px-4 py-2 text-sm font-medium text-[#344054] hover:bg-[#f8fafc]"
            >
              Back to Companies
            </Link>
            {companyQuery.data ? (
              <>
                <button
                  type="button"
                  onClick={openEdit}
                  className="rounded bg-[#172033] px-4 py-2 text-sm font-medium text-white hover:bg-[#24314a]"
                >
                  Edit Company
                </button>
                <button
                  type="button"
                  onClick={openDelete}
                  className="rounded bg-[#b42318] px-4 py-2 text-sm font-medium text-white hover:bg-[#991b1b]"
                >
                  Delete Company
                </button>
              </>
            ) : null}
          </>
        }
      />

      {companyQuery.isLoading ? <LoadingState /> : null}

      {isNotFound ? (
        <PageError
          title="Company not found"
          message="The company no longer exists or the id is incorrect."
        />
      ) : null}

      {companyQuery.isError && !isNotFound ? (
        <PageError
          title="Company could not load"
          message={
            companyQuery.error instanceof Error
              ? companyQuery.error.message
              : "Check the backend API."
          }
          onRetry={() => companyQuery.refetch()}
        />
      ) : null}

      {companyQuery.data ? (
        <div className="space-y-6">
          <CompanyOverview company={companyQuery.data} />
          <CompanyPages
            companyId={companyId}
            pages={pagesQuery.data?.items}
            isLoading={pagesQuery.isLoading}
            error={pagesQuery.error}
          />
          <CompanyJobs jobs={jobsQuery.data?.items} error={jobsQuery.error} />
          <CompanyTechStack
            items={techStackQuery.data}
            error={techStackQuery.error}
          />
          <CompanyCrawlRuns
            runs={crawlRunsQuery.data?.items}
            error={crawlRunsQuery.error}
          />
          <CompanyAgentRuns
            runs={agentRunsQuery.data?.items}
            error={agentRunsQuery.error}
          />
        </div>
      ) : null}

      {isEditOpen && companyQuery.data ? (
        <div className="fixed inset-0 z-50 overflow-y-auto bg-[#101828]/40 px-4 py-6 sm:py-10">
          <div className="mx-auto max-w-3xl rounded-md bg-white shadow-xl">
            <div className="flex items-start justify-between gap-4 border-b border-[#edf0f5] px-5 py-4">
              <div>
                <h2 className="text-lg font-semibold text-[#171923]">
                  Edit Company
                </h2>
                <p className="mt-1 text-sm text-[#667085]">
                  Update {companyQuery.data.name}'s profile details.
                </p>
              </div>
              <button
                type="button"
                onClick={closeEdit}
                className="rounded border border-[#c8ced8] px-2.5 py-1.5 text-sm text-[#475467] hover:bg-[#f8fafc]"
              >
                Close
              </button>
            </div>
            <div className="px-5 py-5">
              <CompanyForm
                mode="edit"
                initialValues={companyQuery.data}
                isSubmitting={updateCompany.isPending}
                submitError={updateCompany.error}
                onSubmit={handleUpdateCompany}
                onCancel={closeEdit}
              />
            </div>
          </div>
        </div>
      ) : null}

      {isDeleteOpen && companyQuery.data ? (
        <div className="fixed inset-0 z-50 grid place-items-center bg-[#101828]/40 px-4 py-6">
          <div className="w-full max-w-md rounded-md bg-white p-5 shadow-xl">
            <h2 className="text-lg font-semibold text-[#171923]">
              Delete Company
            </h2>
            <p className="mt-2 text-sm leading-6 text-[#475467]">
              Delete {companyQuery.data.name}? This removes the company from the
              ScoutAI workspace.
            </p>
            {deleteCompany.error ? (
              <div className="mt-4 rounded-md border border-[#fecaca] bg-[#fff7f7] p-3 text-sm text-[#991b1b]">
                {deleteCompany.error instanceof Error
                  ? deleteCompany.error.message
                  : "Company could not be deleted."}
              </div>
            ) : null}
            <div className="mt-5 flex justify-end gap-3">
              <button
                type="button"
                onClick={closeDelete}
                disabled={deleteCompany.isPending}
                className="rounded border border-[#c8ced8] bg-white px-4 py-2 text-sm font-medium text-[#344054] hover:bg-[#f8fafc] disabled:cursor-not-allowed disabled:opacity-60"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleDeleteCompany}
                disabled={deleteCompany.isPending}
                className="rounded bg-[#b42318] px-4 py-2 text-sm font-medium text-white hover:bg-[#991b1b] disabled:cursor-not-allowed disabled:opacity-60"
              >
                {deleteCompany.isPending ? "Deleting..." : "Delete Company"}
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </>
  );
}
