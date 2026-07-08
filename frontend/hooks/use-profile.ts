import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { dashboardKeys } from "@/hooks/use-dashboard";
import { ApiError } from "@/lib/api";
import {
  createOrReplaceProfile,
  getProfile,
  updateProfile,
} from "@/lib/profile-api";
import type {
  UserProfileCreateInput,
  UserProfileUpdateInput,
} from "@/types/profile";

export const profileKeys = {
  all: ["profile"] as const,
};

export function isProfileNotFound(error: unknown) {
  return error instanceof ApiError && error.status === 404;
}

export function useProfile() {
  return useQuery({
    queryKey: profileKeys.all,
    queryFn: getProfile,
    retry: (failureCount, error) => !isProfileNotFound(error) && failureCount < 2,
  });
}

export function useCreateOrReplaceProfile() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: UserProfileCreateInput) => createOrReplaceProfile(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: profileKeys.all });
      queryClient.invalidateQueries({ queryKey: dashboardKeys.all });
    },
  });
}

export function useUpdateProfile() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: UserProfileUpdateInput) => updateProfile(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: profileKeys.all });
      queryClient.invalidateQueries({ queryKey: dashboardKeys.all });
    },
  });
}
