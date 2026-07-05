"use client";

import { useState, type ReactNode } from "react";

import { CompanyPageForm } from "@/components/companies/CompanyPageForm";
import type { CompanyPage } from "@/types/company-page";
import {
  EmptyState,
  formatDateTime,
  formatLabel,
  formatNumber,
  SectionError,
  SectionShell,
} from "@/components/companies/detail-format";
import {
  useCompanyPage,
  useCreateCompanyPage,
  useDeleteCompanyPage,
  useUpdateCompanyPage,
} from "@/hooks/use-company-pages";
import type {
  CompanyPageCreateInput,
  CompanyPageUpdateInput,
} from "@/types/company-page";

export function CompanyPages({
  companyId,
  pages,
  isLoading = false,
  error,
}: {
  companyId: string;
  pages?: CompanyPage[];
  isLoading?: boolean;
  error?: Error | null;
}) {
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [viewingPageId, setViewingPageId] = useState<string | null>(null);
  const [editingPage, setEditingPage] = useState<CompanyPage | null>(null);
  const [deletingPage, setDeletingPage] = useState<CompanyPage | null>(null);
  const createPage = useCreateCompanyPage(companyId);
  const updatePage = useUpdateCompanyPage();
  const deletePage = useDeleteCompanyPage(companyId);
  const pageDetail = useCompanyPage(viewingPageId);

  function openCreate() {
    createPage.reset();
    setIsCreateOpen(true);
  }

  function closeCreate() {
    createPage.reset();
    setIsCreateOpen(false);
  }

  async function handleCreatePage(input: CompanyPageCreateInput) {
    await createPage.mutateAsync(input);
    closeCreate();
  }

  function openEdit(page: CompanyPage) {
    updatePage.reset();
    setEditingPage(page);
  }

  function closeEdit() {
    updatePage.reset();
    setEditingPage(null);
  }

  async function handleUpdatePage(input: CompanyPageUpdateInput) {
    if (!editingPage) {
      return;
    }

    await updatePage.mutateAsync({
      pageId: editingPage.id,
      companyId,
      data: input,
    });
    closeEdit();
  }

  function openDelete(page: CompanyPage) {
    deletePage.reset();
    setDeletingPage(page);
  }

  function closeDelete() {
    deletePage.reset();
    setDeletingPage(null);
  }

  async function handleDeletePage() {
    if (!deletingPage) {
      return;
    }

    await deletePage.mutateAsync(deletingPage.id);
    closeDelete();
  }

  return (
    <SectionShell title="Pages">
      <div className="mb-4 flex items-center justify-between gap-3">
        <p className="text-sm text-[#667085]">
          Manually tracked pages for this company.
        </p>
        <button
          type="button"
          onClick={openCreate}
          className="rounded bg-[#172033] px-3 py-2 text-sm font-medium text-white hover:bg-[#24314a]"
        >
          Add Page
        </button>
      </div>

      {isLoading ? (
        <div className="space-y-3">
          {Array.from({ length: 3 }).map((_, index) => (
            <div
              key={index}
              className="h-10 animate-pulse rounded bg-[#eef2f6]"
            />
          ))}
        </div>
      ) : null}

      {error ? <SectionError message={error.message} /> : null}
      {!isLoading && !error && pages?.length === 0 ? (
        <EmptyState message="No company pages found." />
      ) : null}
      {!isLoading && !error && pages && pages.length > 0 ? (
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
                <th className="px-3 py-2 font-semibold">Created</th>
                <th className="px-3 py-2 text-right font-semibold">Actions</th>
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
                  <td className="whitespace-nowrap px-3 py-3 text-[#475467]">
                    {formatDateTime(page.created_at)}
                  </td>
                  <td className="whitespace-nowrap px-3 py-3 text-right">
                    <div className="flex justify-end gap-2">
                      <a
                        href={page.url}
                        target="_blank"
                        rel="noreferrer"
                        className="rounded border border-[#c8ced8] bg-white px-2.5 py-1.5 text-xs font-medium text-[#344054] hover:bg-[#f8fafc]"
                      >
                        Open
                      </a>
                      <button
                        type="button"
                        onClick={() => setViewingPageId(page.id)}
                        className="rounded border border-[#c8ced8] bg-white px-2.5 py-1.5 text-xs font-medium text-[#344054] hover:bg-[#f8fafc]"
                      >
                        View
                      </button>
                      <button
                        type="button"
                        onClick={() => openEdit(page)}
                        className="rounded border border-[#c8ced8] bg-white px-2.5 py-1.5 text-xs font-medium text-[#344054] hover:bg-[#f8fafc]"
                      >
                        Edit
                      </button>
                      <button
                        type="button"
                        onClick={() => openDelete(page)}
                        disabled={deletePage.isPending && deletingPage?.id === page.id}
                        className="rounded border border-[#fca5a5] bg-white px-2.5 py-1.5 text-xs font-medium text-[#b42318] hover:bg-[#fff7f7] disabled:cursor-not-allowed disabled:opacity-60"
                      >
                        {deletePage.isPending && deletingPage?.id === page.id
                          ? "Deleting..."
                          : "Delete"}
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}

      {isCreateOpen ? (
        <Modal title="Add Page" onClose={closeCreate}>
          <CompanyPageForm
            isSubmitting={createPage.isPending}
            submitError={createPage.error}
            onSubmit={handleCreatePage}
            onCancel={closeCreate}
          />
        </Modal>
      ) : null}

      {editingPage ? (
        <Modal title="Edit Page" onClose={closeEdit}>
          <CompanyPageForm
            mode="edit"
            initialValues={editingPage}
            isSubmitting={updatePage.isPending}
            submitError={updatePage.error}
            onSubmit={handleUpdatePage}
            onCancel={closeEdit}
          />
        </Modal>
      ) : null}

      {viewingPageId ? (
        <Modal title="Page Details" onClose={() => setViewingPageId(null)}>
          {pageDetail.isLoading ? (
            <div className="h-24 animate-pulse rounded bg-[#eef2f6]" />
          ) : null}
          {pageDetail.error ? (
            <SectionError
              message={
                pageDetail.error instanceof Error
                  ? pageDetail.error.message
                  : "Page could not load."
              }
            />
          ) : null}
          {pageDetail.data ? <PageDetail page={pageDetail.data} /> : null}
        </Modal>
      ) : null}

      {deletingPage ? (
        <div className="fixed inset-0 z-50 grid place-items-center bg-[#101828]/40 px-4 py-6">
          <div className="w-full max-w-md rounded-md bg-white p-5 shadow-xl">
            <h3 className="text-lg font-semibold text-[#171923]">
              Delete Page
            </h3>
            <p className="mt-2 text-sm leading-6 text-[#475467]">
              Delete {deletingPage.url}? This removes the manually tracked page
              from this company.
            </p>
            {deletePage.error ? (
              <div className="mt-4 rounded-md border border-[#fecaca] bg-[#fff7f7] p-3 text-sm text-[#991b1b]">
                {deletePage.error instanceof Error
                  ? deletePage.error.message
                  : "Page could not be deleted."}
              </div>
            ) : null}
            <div className="mt-5 flex justify-end gap-3">
              <button
                type="button"
                onClick={closeDelete}
                disabled={deletePage.isPending}
                className="rounded border border-[#c8ced8] bg-white px-4 py-2 text-sm font-medium text-[#344054] hover:bg-[#f8fafc] disabled:cursor-not-allowed disabled:opacity-60"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleDeletePage}
                disabled={deletePage.isPending}
                className="rounded bg-[#b42318] px-4 py-2 text-sm font-medium text-white hover:bg-[#991b1b] disabled:cursor-not-allowed disabled:opacity-60"
              >
                {deletePage.isPending ? "Deleting..." : "Delete Page"}
              </button>
            </div>
          </div>
        </div>
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
      <div className="mx-auto max-w-3xl rounded-md bg-white shadow-xl">
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

function PageDetail({ page }: { page: CompanyPage }) {
  return (
    <div className="space-y-4">
      <div className="grid gap-4 sm:grid-cols-2">
        <DetailItem label="URL" value={page.url} />
        <DetailItem label="Type" value={formatLabel(page.page_type)} />
        <DetailItem label="Title" value={page.title ?? "None"} />
        <DetailItem label="Status Code" value={page.status_code ?? "None"} />
        <DetailItem
          label="Content Length"
          value={formatNumber(page.content_length)}
        />
        <DetailItem label="HTML Hash" value={page.html_hash ?? "None"} />
        <DetailItem
          label="Last Crawled"
          value={formatDateTime(page.last_crawled_at)}
        />
        <DetailItem label="Created" value={formatDateTime(page.created_at)} />
      </div>
      <div>
        <h4 className="text-sm font-semibold text-[#171923]">Raw Text</h4>
        <pre className="mt-2 max-h-80 overflow-auto whitespace-pre-wrap rounded-md border border-[#edf0f5] bg-[#f8fafc] p-3 text-xs leading-5 text-[#475467]">
          {page.raw_text ?? "None"}
        </pre>
      </div>
    </div>
  );
}

function DetailItem({
  label,
  value,
}: {
  label: string;
  value: string | number;
}) {
  return (
    <div>
      <dt className="text-xs font-medium uppercase text-[#667085]">{label}</dt>
      <dd className="mt-1 break-words text-sm text-[#171923]">{value}</dd>
    </div>
  );
}
