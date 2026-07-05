"use client";

import { useState, type ReactNode } from "react";

import {
  EmptyState,
  formatDateTime,
  formatLabel,
  SectionError,
  SectionShell,
} from "@/components/companies/detail-format";
import { TechStackForm } from "@/components/tech-stack/TechStackForm";
import {
  useCreateTechStackItem,
  useDeleteTechStackItem,
  useUpdateTechStackItem,
} from "@/hooks/use-tech-stack";
import type {
  TechStackItem,
  TechStackItemCreateInput,
  TechStackItemUpdateInput,
} from "@/types/tech-stack";

function confidencePercent(value: number) {
  return `${Math.round(value * 100)}%`;
}

export function CompanyTechStack({
  companyId,
  items,
  isLoading = false,
  error,
}: {
  companyId: string;
  items?: TechStackItem[];
  isLoading?: boolean;
  error?: Error | null;
}) {
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [viewingItem, setViewingItem] = useState<TechStackItem | null>(null);
  const [editingItem, setEditingItem] = useState<TechStackItem | null>(null);
  const [deletingItem, setDeletingItem] = useState<TechStackItem | null>(null);
  const createItem = useCreateTechStackItem(companyId);
  const updateItem = useUpdateTechStackItem(companyId);
  const deleteItem = useDeleteTechStackItem(companyId);

  function openCreate() {
    createItem.reset();
    setIsCreateOpen(true);
  }

  function closeCreate() {
    createItem.reset();
    setIsCreateOpen(false);
  }

  async function handleCreateItem(input: TechStackItemCreateInput) {
    await createItem.mutateAsync(input);
    closeCreate();
  }

  function openEdit(item: TechStackItem) {
    updateItem.reset();
    setEditingItem(item);
  }

  function closeEdit() {
    updateItem.reset();
    setEditingItem(null);
  }

  async function handleUpdateItem(input: TechStackItemUpdateInput) {
    if (!editingItem) {
      return;
    }

    await updateItem.mutateAsync({
      itemId: editingItem.id,
      data: input,
    });
    closeEdit();
  }

  function openDelete(item: TechStackItem) {
    deleteItem.reset();
    setDeletingItem(item);
  }

  function closeDelete() {
    deleteItem.reset();
    setDeletingItem(null);
  }

  async function handleDeleteItem() {
    if (!deletingItem) {
      return;
    }

    await deleteItem.mutateAsync(deletingItem.id);
    closeDelete();
  }

  return (
    <SectionShell title="Tech Stack">
      <div className="mb-4 flex items-center justify-between gap-3">
        <p className="text-sm text-[#667085]">
          Manually tracked technologies for this company.
        </p>
        <button
          type="button"
          onClick={openCreate}
          className="rounded bg-[#172033] px-3 py-2 text-sm font-medium text-white hover:bg-[#24314a]"
        >
          Add Technology
        </button>
      </div>

      {isLoading ? (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 3 }).map((_, index) => (
            <div
              key={index}
              className="h-28 animate-pulse rounded border border-[#edf0f5] bg-[#eef2f6]"
            />
          ))}
        </div>
      ) : null}

      {error ? <SectionError message={error.message} /> : null}
      {!isLoading && !error && items?.length === 0 ? (
        <EmptyState message="No tech stack items found." />
      ) : null}
      {!isLoading && !error && items && items.length > 0 ? (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {items.map((item) => (
            <article
              key={item.id}
              className="rounded-md border border-[#edf0f5] p-4"
            >
              <div className="flex items-start justify-between gap-3">
                <div>
                  <h3 className="text-sm font-semibold text-[#171923]">
                    {item.name}
                  </h3>
                  <p className="mt-1 text-sm text-[#667085]">
                    {formatLabel(item.category)} -{" "}
                    {formatLabel(item.source ?? "other")}
                  </p>
                </div>
                <span className="rounded bg-[#eef2f6] px-2 py-1 text-xs font-medium text-[#475467]">
                  {confidencePercent(item.confidence)}
                </span>
              </div>
              <p className="mt-3 text-sm text-[#475467]">
                Created: {formatDateTime(item.created_at)}
              </p>
              <div className="mt-4 flex flex-wrap justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setViewingItem(item)}
                  className="rounded border border-[#c8ced8] bg-white px-2.5 py-1.5 text-xs font-medium text-[#344054] hover:bg-[#f8fafc]"
                >
                  View
                </button>
                <button
                  type="button"
                  onClick={() => openEdit(item)}
                  className="rounded border border-[#c8ced8] bg-white px-2.5 py-1.5 text-xs font-medium text-[#344054] hover:bg-[#f8fafc]"
                >
                  Edit
                </button>
                <button
                  type="button"
                  onClick={() => openDelete(item)}
                  disabled={deleteItem.isPending && deletingItem?.id === item.id}
                  className="rounded border border-[#fca5a5] bg-white px-2.5 py-1.5 text-xs font-medium text-[#b42318] hover:bg-[#fff7f7] disabled:cursor-not-allowed disabled:opacity-60"
                >
                  {deleteItem.isPending && deletingItem?.id === item.id
                    ? "Deleting..."
                    : "Delete"}
                </button>
              </div>
            </article>
          ))}
        </div>
      ) : null}

      {isCreateOpen ? (
        <Modal title="Add Technology" onClose={closeCreate}>
          <TechStackForm
            isSubmitting={createItem.isPending}
            submitError={createItem.error}
            onSubmit={handleCreateItem}
            onCancel={closeCreate}
          />
        </Modal>
      ) : null}

      {editingItem ? (
        <Modal title="Edit Technology" onClose={closeEdit}>
          <TechStackForm
            mode="edit"
            initialValues={editingItem}
            isSubmitting={updateItem.isPending}
            submitError={updateItem.error}
            onSubmit={handleUpdateItem}
            onCancel={closeEdit}
          />
        </Modal>
      ) : null}

      {viewingItem ? (
        <Modal title="Technology Details" onClose={() => setViewingItem(null)}>
          <div className="grid gap-4 sm:grid-cols-2">
            <DetailItem label="Name" value={viewingItem.name} />
            <DetailItem
              label="Category"
              value={formatLabel(viewingItem.category)}
            />
            <DetailItem
              label="Source"
              value={formatLabel(viewingItem.source ?? "other")}
            />
            <DetailItem
              label="Confidence"
              value={confidencePercent(viewingItem.confidence)}
            />
            <DetailItem
              label="Created"
              value={formatDateTime(viewingItem.created_at)}
            />
            <DetailItem
              label="Updated"
              value={formatDateTime(viewingItem.updated_at)}
            />
          </div>
        </Modal>
      ) : null}

      {deletingItem ? (
        <div className="fixed inset-0 z-50 grid place-items-center bg-[#101828]/40 px-4 py-6">
          <div className="w-full max-w-md rounded-md bg-white p-5 shadow-xl">
            <h3 className="text-lg font-semibold text-[#171923]">
              Delete Technology
            </h3>
            <p className="mt-2 text-sm leading-6 text-[#475467]">
              Delete {deletingItem.name}? This removes it from the company tech
              stack.
            </p>
            {deleteItem.error ? (
              <div className="mt-4 rounded-md border border-[#fecaca] bg-[#fff7f7] p-3 text-sm text-[#991b1b]">
                {deleteItem.error instanceof Error
                  ? deleteItem.error.message
                  : "Technology could not be deleted."}
              </div>
            ) : null}
            <div className="mt-5 flex justify-end gap-3">
              <button
                type="button"
                onClick={closeDelete}
                disabled={deleteItem.isPending}
                className="rounded border border-[#c8ced8] bg-white px-4 py-2 text-sm font-medium text-[#344054] hover:bg-[#f8fafc] disabled:cursor-not-allowed disabled:opacity-60"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleDeleteItem}
                disabled={deleteItem.isPending}
                className="rounded bg-[#b42318] px-4 py-2 text-sm font-medium text-white hover:bg-[#991b1b] disabled:cursor-not-allowed disabled:opacity-60"
              >
                {deleteItem.isPending ? "Deleting..." : "Delete Technology"}
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
      <div className="mx-auto max-w-2xl rounded-md bg-white shadow-xl">
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
