"use client";

import Link from "next/link";
import { useParams } from "next/navigation";

import { CompanyAgentRuns } from "@/components/companies/CompanyAgentRuns";
import { CompanyCrawlRuns } from "@/components/companies/CompanyCrawlRuns";
import { CompanyJobs } from "@/components/companies/CompanyJobs";
import { CompanyOverview } from "@/components/companies/CompanyOverview";
import { CompanyPages } from "@/components/companies/CompanyPages";
import { CompanyTechStack } from "@/components/companies/CompanyTechStack";
import { PageHeader } from "@/components/layout/PageHeader";
import { ApiError } from "@/lib/api";
import { useCompanyAgentRuns } from "@/hooks/use-agent-runs";
import { useCompany } from "@/hooks/use-companies";
import { useCompanyPages } from "@/hooks/use-company-pages";
import { useCompanyCrawlRuns } from "@/hooks/use-crawl-runs";
import { useCompanyJobs } from "@/hooks/use-jobs";
import { useCompanyTechStack } from "@/hooks/use-tech-stack";

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
  const companyId = params.id;
  const companyQuery = useCompany(companyId);
  const pagesQuery = useCompanyPages(companyId);
  const jobsQuery = useCompanyJobs(companyId);
  const techStackQuery = useCompanyTechStack(companyId);
  const crawlRunsQuery = useCompanyCrawlRuns(companyId);
  const agentRunsQuery = useCompanyAgentRuns(companyId);

  const isNotFound =
    companyQuery.error instanceof ApiError && companyQuery.error.status === 404;

  return (
    <>
      <PageHeader
        title="Company Detail"
        description="Read-only company profile and related ScoutAI activity."
        actions={
          <Link
            href="/companies"
            className="rounded border border-[#c8ced8] bg-white px-4 py-2 text-sm font-medium text-[#344054] hover:bg-[#f8fafc]"
          >
            Back to Companies
          </Link>
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
            pages={pagesQuery.data?.items}
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
    </>
  );
}
