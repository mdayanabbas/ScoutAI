"use client";

import { useState } from "react";

import { CompanyForm } from "@/components/companies/CompanyForm";
import { CompanyTable } from "@/components/companies/CompanyTable";
import { PageHeader } from "@/components/layout/PageHeader";
import {
  useCompanies,
  useCreateCompany,
  useDeleteCompany,
  useUpdateCompany,
} from "@/hooks/use-companies";
import type {
  Company,
  CompanyCreateInput,
  CompanyUpdateInput,
} from "@/types/company";

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
  const updateCompany = useUpdateCompany();
  const deleteCompany = useDeleteCompany();
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [editingCompany, setEditingCompany] = useState<Company | null>(null);
  const [deletingCompany, setDeletingCompany] = useState<Company | null>(null);

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

  function openEdit(company: Company) {
    updateCompany.reset();
    setEditingCompany(company);
  }

  function closeEdit() {
    updateCompany.reset();
    setEditingCompany(null);
  }

  async function handleUpdateCompany(input: CompanyUpdateInput) {
    if (!editingCompany) {
      return;
    }

    await updateCompany.mutateAsync({
      id: editingCompany.id,
      data: input,
    });
    closeEdit();
  }

  function openDelete(company: Company) {
    deleteCompany.reset();
    setDeletingCompany(company);
  }

  function closeDelete() {
    deleteCompany.reset();
    setDeletingCompany(null);
  }

  async function handleDeleteCompany() {
    if (!deletingCompany) {
      return;
    }

    await deleteCompany.mutateAsync(deletingCompany.id);
    closeDelete();
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
          <CompanyTable
            companies={data.items}
            onEdit={openEdit}
            onDelete={openDelete}
            deletingCompanyId={
              deleteCompany.isPending ? deletingCompany?.id ?? null : null
            }
          />
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

      {editingCompany ? (
        <div className="fixed inset-0 z-50 overflow-y-auto bg-[#101828]/40 px-4 py-6 sm:py-10">
          <div className="mx-auto max-w-3xl rounded-md bg-white shadow-xl">
            <div className="flex items-start justify-between gap-4 border-b border-[#edf0f5] px-5 py-4">
              <div>
                <h2 className="text-lg font-semibold text-[#171923]">
                  Edit Company
                </h2>
                <p className="mt-1 text-sm text-[#667085]">
                  Update {editingCompany.name}&apos;s profile details.
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
                initialValues={editingCompany}
                isSubmitting={updateCompany.isPending}
                submitError={updateCompany.error}
                onSubmit={handleUpdateCompany}
                onCancel={closeEdit}
              />
            </div>
          </div>
        </div>
      ) : null}

      {deletingCompany ? (
        <div className="fixed inset-0 z-50 grid place-items-center bg-[#101828]/40 px-4 py-6">
          <div className="w-full max-w-md rounded-md bg-white p-5 shadow-xl">
            <h2 className="text-lg font-semibold text-[#171923]">
              Delete Company
            </h2>
            <p className="mt-2 text-sm leading-6 text-[#475467]">
              Delete {deletingCompany.name}? This removes the company from the
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
