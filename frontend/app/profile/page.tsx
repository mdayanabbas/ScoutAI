"use client";

import { useState } from "react";

import { ProfileForm } from "@/components/profile/ProfileForm";
import { ProfileSummary } from "@/components/profile/ProfileSummary";
import { PageHeader } from "@/components/layout/PageHeader";
import {
  isProfileNotFound,
  useCreateOrReplaceProfile,
  useProfile,
  useUpdateProfile,
} from "@/hooks/use-profile";
import type { UserProfileCreateInput } from "@/types/profile";

export default function ProfilePage() {
  const profileQuery = useProfile();
  const createProfile = useCreateOrReplaceProfile();
  const updateProfile = useUpdateProfile();
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const isCreateMode =
    profileQuery.isError && isProfileNotFound(profileQuery.error);
  const hasProfile = Boolean(profileQuery.data);
  const pageError = profileQuery.isError && !isCreateMode;

  async function handleCreate(data: UserProfileCreateInput) {
    setSuccessMessage(null);
    await createProfile.mutateAsync(data);
    setSuccessMessage("Profile created successfully");
  }

  async function handleUpdate(data: UserProfileCreateInput) {
    setSuccessMessage(null);
    await updateProfile.mutateAsync(data);
    setSuccessMessage("Profile updated successfully");
  }

  return (
    <>
      <PageHeader
        title="Profile"
        description="Create your candidate profile so ScoutAI can later understand which startups and roles are relevant to you."
      />

      {profileQuery.isLoading ? <ProfileSkeleton /> : null}

      {pageError ? (
        <div className="rounded-md border border-[#fecaca] bg-[#fff7f7] p-4">
          <h2 className="text-sm font-semibold text-[#991b1b]">
            Profile could not load
          </h2>
          <p className="mt-1 text-sm text-[#7f1d1d]">
            {profileQuery.error instanceof Error
              ? profileQuery.error.message
              : "Check the backend API."}
          </p>
          <button
            type="button"
            onClick={() => profileQuery.refetch()}
            className="mt-4 rounded bg-[#172033] px-3 py-2 text-sm font-medium text-white"
          >
            Retry
          </button>
        </div>
      ) : null}

      {isCreateMode ? (
        <div className="space-y-5">
          <div className="rounded-md border border-[#d9dee8] bg-white p-4">
            <h2 className="text-base font-semibold text-[#171923]">
              Create your profile
            </h2>
            <p className="mt-1 text-sm leading-6 text-[#667085]">
              Create your profile so ScoutAI can understand which startups and
              roles are relevant to you.
            </p>
          </div>
          <ProfileForm
            mode="create"
            onSubmit={handleCreate}
            isSubmitting={createProfile.isPending}
            apiError={createProfile.error}
            successMessage={successMessage}
          />
        </div>
      ) : null}

      {hasProfile ? (
        <div className="grid gap-6 lg:grid-cols-[280px_1fr]">
          <ProfileSummary profile={profileQuery.data!} />
          <ProfileForm
            mode="edit"
            initialValues={profileQuery.data}
            onSubmit={handleUpdate}
            isSubmitting={updateProfile.isPending}
            apiError={updateProfile.error}
            successMessage={successMessage}
          />
        </div>
      ) : null}
    </>
  );
}

function ProfileSkeleton() {
  return (
    <div className="grid gap-6 lg:grid-cols-[280px_1fr]">
      <div className="h-64 animate-pulse rounded-md border border-[#d9dee8] bg-white" />
      <div className="space-y-4">
        {Array.from({ length: 4 }).map((_, index) => (
          <div
            key={index}
            className="h-36 animate-pulse rounded-md border border-[#d9dee8] bg-white"
          />
        ))}
      </div>
    </div>
  );
}
