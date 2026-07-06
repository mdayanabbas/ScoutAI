"use client";

import { FormEvent, useState, type ReactNode } from "react";

import {
  EmptyState,
  formatDateTime,
  formatNumber,
  SectionError,
  SectionShell,
  StatusBadge,
} from "@/components/companies/detail-format";
import {
  useCreateCompanyCrawlRun,
  useMarkCrawlRunFailed,
  useMarkCrawlRunRunning,
  useMarkCrawlRunSuccess,
} from "@/hooks/use-crawl-runs";
import type {
  CrawlRun,
  CrawlRunMarkFailedInput,
  CrawlRunMarkSuccessInput,
} from "@/types/crawl-run";

export function CompanyCrawlRuns({
  companyId,
  runs,
  isLoading = false,
  error,
}: {
  companyId: string;
  runs?: CrawlRun[];
  isLoading?: boolean;
  error?: Error | null;
}) {
  const [successRun, setSuccessRun] = useState<CrawlRun | null>(null);
  const [failedRun, setFailedRun] = useState<CrawlRun | null>(null);
  const createRun = useCreateCompanyCrawlRun(companyId);
  const markRunning = useMarkCrawlRunRunning(companyId);
  const markSuccess = useMarkCrawlRunSuccess(companyId);
  const markFailed = useMarkCrawlRunFailed(companyId);

  async function handleCreateRun() {
    await createRun.mutateAsync();
  }

  async function handleMarkRunning(crawlRunId: string) {
    await markRunning.mutateAsync(crawlRunId);
  }

  async function handleMarkSuccess(data: CrawlRunMarkSuccessInput) {
    if (!successRun) {
      return;
    }

    await markSuccess.mutateAsync({
      crawlRunId: successRun.id,
      data,
    });
    setSuccessRun(null);
  }

  async function handleMarkFailed(data: CrawlRunMarkFailedInput) {
    if (!failedRun) {
      return;
    }

    await markFailed.mutateAsync({
      crawlRunId: failedRun.id,
      data,
    });
    setFailedRun(null);
  }

  return (
    <SectionShell title="Crawl Runs">
      <div className="mb-4 flex items-center justify-between gap-3">
        <p className="text-sm text-[#667085]">
          Create and update crawl tracking records. This does not crawl websites.
        </p>
        <button
          type="button"
          onClick={handleCreateRun}
          disabled={createRun.isPending}
          className="rounded bg-[#172033] px-3 py-2 text-sm font-medium text-white hover:bg-[#24314a] disabled:cursor-not-allowed disabled:opacity-60"
        >
          {createRun.isPending ? "Creating..." : "Create Crawl Run"}
        </button>
      </div>

      {createRun.error ? (
        <SectionError
          message={
            createRun.error instanceof Error
              ? createRun.error.message
              : "Crawl run could not be created."
          }
        />
      ) : null}

      {isLoading ? (
        <div className="space-y-3">
          {Array.from({ length: 3 }).map((_, index) => (
            <div
              key={index}
              className="h-24 animate-pulse rounded bg-[#eef2f6]"
            />
          ))}
        </div>
      ) : null}

      {error ? <SectionError message={error.message} /> : null}
      {!isLoading && !error && runs?.length === 0 ? (
        <EmptyState message="No crawl runs found." />
      ) : null}
      {!isLoading && !error && runs && runs.length > 0 ? (
        <div className="space-y-3">
          {runs.map((run) => {
            const canMarkRunning = run.status === "pending";
            const canComplete =
              run.status === "pending" || run.status === "running";

            return (
              <article
                key={run.id}
                className="rounded-md border border-[#edf0f5] p-4"
              >
                <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                  <StatusBadge value={run.status} />
                  <span className="text-sm text-[#667085]">
                    Created: {formatDateTime(run.created_at)}
                  </span>
                </div>
                <div className="mt-3 grid gap-3 text-sm text-[#475467] sm:grid-cols-2 lg:grid-cols-4">
                  <span>Started: {formatDateTime(run.started_at)}</span>
                  <span>Finished: {formatDateTime(run.finished_at)}</span>
                  <span>Pages found: {formatNumber(run.pages_found)}</span>
                  <span>Pages crawled: {formatNumber(run.pages_crawled)}</span>
                  <span className="lg:col-span-4">
                    Error: {run.error_message ?? "None"}
                  </span>
                </div>
                {canMarkRunning || canComplete ? (
                  <div className="mt-4 flex flex-wrap justify-end gap-2">
                    {canMarkRunning ? (
                      <button
                        type="button"
                        onClick={() => handleMarkRunning(run.id)}
                        disabled={markRunning.isPending}
                        className="rounded border border-[#c8ced8] bg-white px-2.5 py-1.5 text-xs font-medium text-[#344054] hover:bg-[#f8fafc] disabled:cursor-not-allowed disabled:opacity-60"
                      >
                        {markRunning.isPending ? "Updating..." : "Mark Running"}
                      </button>
                    ) : null}
                    {canComplete ? (
                      <>
                        <button
                          type="button"
                          onClick={() => {
                            markSuccess.reset();
                            setSuccessRun(run);
                          }}
                          className="rounded border border-[#86efac] bg-white px-2.5 py-1.5 text-xs font-medium text-[#166534] hover:bg-[#f0fdf4]"
                        >
                          Mark Success
                        </button>
                        <button
                          type="button"
                          onClick={() => {
                            markFailed.reset();
                            setFailedRun(run);
                          }}
                          className="rounded border border-[#fca5a5] bg-white px-2.5 py-1.5 text-xs font-medium text-[#b42318] hover:bg-[#fff7f7]"
                        >
                          Mark Failed
                        </button>
                      </>
                    ) : null}
                  </div>
                ) : null}
              </article>
            );
          })}
        </div>
      ) : null}

      {successRun ? (
        <Modal title="Mark Crawl Run Success" onClose={() => setSuccessRun(null)}>
          <MarkSuccessForm
            isSubmitting={markSuccess.isPending}
            submitError={markSuccess.error}
            onSubmit={handleMarkSuccess}
            onCancel={() => setSuccessRun(null)}
          />
        </Modal>
      ) : null}

      {failedRun ? (
        <Modal title="Mark Crawl Run Failed" onClose={() => setFailedRun(null)}>
          <MarkFailedForm
            isSubmitting={markFailed.isPending}
            submitError={markFailed.error}
            onSubmit={handleMarkFailed}
            onCancel={() => setFailedRun(null)}
          />
        </Modal>
      ) : null}
    </SectionShell>
  );
}

function Modal({
  title,
  children,
  onClose,
}: {
  title: string;
  children: ReactNode;
  onClose: () => void;
}) {
  return (
    <div className="fixed inset-0 z-50 overflow-y-auto bg-[#101828]/40 px-4 py-6 sm:py-10">
      <div className="mx-auto max-w-md rounded-md bg-white shadow-xl">
        <div className="flex items-start justify-between gap-4 border-b border-[#edf0f5] px-5 py-4">
          <h3 className="text-lg font-semibold text-[#171923]">{title}</h3>
          <button
            type="button"
            onClick={onClose}
            className="rounded border border-[#c8ced8] px-2.5 py-1.5 text-sm text-[#475467] hover:bg-[#f8fafc]"
          >
            Close
          </button>
        </div>
        <div className="px-5 py-5">{children}</div>
      </div>
    </div>
  );
}

function MarkSuccessForm({
  isSubmitting,
  submitError,
  onSubmit,
  onCancel,
}: {
  isSubmitting: boolean;
  submitError: unknown;
  onSubmit: (data: CrawlRunMarkSuccessInput) => Promise<void> | void;
  onCancel: () => void;
}) {
  const [pagesFound, setPagesFound] = useState("");
  const [pagesCrawled, setPagesCrawled] = useState("");
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const found = pagesFound.trim() === "" ? null : Number(pagesFound);
    const crawled = pagesCrawled.trim() === "" ? null : Number(pagesCrawled);

    if (found !== null && (!Number.isInteger(found) || found < 0)) {
      setError("Pages found must be a whole number greater than or equal to 0.");
      return;
    }
    if (crawled !== null && (!Number.isInteger(crawled) || crawled < 0)) {
      setError("Pages crawled must be a whole number greater than or equal to 0.");
      return;
    }
    if (found !== null && crawled !== null && crawled > found) {
      setError("Pages crawled cannot be greater than pages found.");
      return;
    }

    setError(null);
    await onSubmit({
      pages_found: found,
      pages_crawled: crawled,
    });
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      {error ? <SectionError message={error} /> : null}
      {submitError ? (
        <SectionError
          message={
            submitError instanceof Error
              ? submitError.message
              : "Crawl run could not be marked successful."
          }
        />
      ) : null}
      <NumberField
        label="Pages Found"
        value={pagesFound}
        onChange={setPagesFound}
      />
      <NumberField
        label="Pages Crawled"
        value={pagesCrawled}
        onChange={setPagesCrawled}
      />
      <FormActions
        submitLabel="Mark Success"
        isSubmitting={isSubmitting}
        onCancel={onCancel}
      />
    </form>
  );
}

function MarkFailedForm({
  isSubmitting,
  submitError,
  onSubmit,
  onCancel,
}: {
  isSubmitting: boolean;
  submitError: unknown;
  onSubmit: (data: CrawlRunMarkFailedInput) => Promise<void> | void;
  onCancel: () => void;
}) {
  const [errorMessage, setErrorMessage] = useState("");
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!errorMessage.trim()) {
      setError("Error message is required.");
      return;
    }

    setError(null);
    await onSubmit({ error_message: errorMessage.trim() });
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      {error ? <SectionError message={error} /> : null}
      {submitError ? (
        <SectionError
          message={
            submitError instanceof Error
              ? submitError.message
              : "Crawl run could not be marked failed."
          }
        />
      ) : null}
      <label className="block">
        <span className="mb-1.5 block text-sm font-medium text-[#344054]">
          Error Message
        </span>
        <textarea
          value={errorMessage}
          onChange={(event) => setErrorMessage(event.target.value)}
          className="min-h-24 w-full rounded border border-[#c8ced8] px-3 py-2 text-sm outline-none focus:border-[#172033]"
        />
      </label>
      <FormActions
        submitLabel="Mark Failed"
        isSubmitting={isSubmitting}
        onCancel={onCancel}
        destructive
      />
    </form>
  );
}

function NumberField({
  label,
  value,
  onChange,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
}) {
  return (
    <label className="block">
      <span className="mb-1.5 block text-sm font-medium text-[#344054]">
        {label}
      </span>
      <input
        type="number"
        min={0}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="w-full rounded border border-[#c8ced8] px-3 py-2 text-sm outline-none focus:border-[#172033]"
      />
    </label>
  );
}

function FormActions({
  submitLabel,
  isSubmitting,
  onCancel,
  destructive = false,
}: {
  submitLabel: string;
  isSubmitting: boolean;
  onCancel: () => void;
  destructive?: boolean;
}) {
  return (
    <div className="flex justify-end gap-3 border-t border-[#edf0f5] pt-4">
      <button
        type="button"
        onClick={onCancel}
        disabled={isSubmitting}
        className="rounded border border-[#c8ced8] bg-white px-4 py-2 text-sm font-medium text-[#344054] hover:bg-[#f8fafc] disabled:cursor-not-allowed disabled:opacity-60"
      >
        Cancel
      </button>
      <button
        type="submit"
        disabled={isSubmitting}
        className={[
          "rounded px-4 py-2 text-sm font-medium text-white disabled:cursor-not-allowed disabled:opacity-60",
          destructive
            ? "bg-[#b42318] hover:bg-[#991b1b]"
            : "bg-[#172033] hover:bg-[#24314a]",
        ].join(" ")}
      >
        {isSubmitting ? "Saving..." : submitLabel}
      </button>
    </div>
  );
}
