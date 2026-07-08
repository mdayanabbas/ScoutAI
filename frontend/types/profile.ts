export type RemotePreference =
  | "unknown"
  | "onsite"
  | "hybrid"
  | "remote_country"
  | "remote_region"
  | "remote_worldwide";

export type UserProfile = {
  id: string;
  display_name: string | null;
  target_roles: string[] | null;
  preferred_locations: string[] | null;
  remote_preference: RemotePreference | null;
  years_experience: number | null;
  skills: string[] | null;
  strong_skills: string[] | null;
  weak_skills: string[] | null;
  preferred_company_stages: string[] | null;
  preferred_company_sizes: string[] | null;
  created_at: string;
  updated_at: string | null;
};

export type UserProfileCreateInput = {
  display_name: string;
  target_roles: string[];
  preferred_locations: string[];
  remote_preference: RemotePreference;
  years_experience: number;
  skills: string[];
  strong_skills: string[];
  weak_skills: string[];
  preferred_company_stages: string[];
  preferred_company_sizes: string[];
};

export type UserProfileUpdateInput = Partial<UserProfileCreateInput>;
