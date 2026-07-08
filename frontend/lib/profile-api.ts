import { api } from "@/lib/api";
import type {
  UserProfile,
  UserProfileCreateInput,
  UserProfileUpdateInput,
} from "@/types/profile";

export function getProfile() {
  return api.get<UserProfile>("/profile");
}

export function createOrReplaceProfile(data: UserProfileCreateInput) {
  return api.put<UserProfile>("/profile", data);
}

export function updateProfile(data: UserProfileUpdateInput) {
  return api.patch<UserProfile>("/profile", data);
}
