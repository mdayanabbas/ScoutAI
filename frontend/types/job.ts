export type RoleCategory =
  | "ai_engineer"
  | "backend_engineer"
  | "software_engineer"
  | "ml_engineer"
  | "data_engineer"
  | "full_stack_engineer"
  | "frontend_engineer"
  | "devops_engineer"
  | "product_engineer"
  | "other";

export type RemoteType =
  | "unknown"
  | "onsite"
  | "hybrid"
  | "remote_country"
  | "remote_region"
  | "remote_worldwide";

export type JobStatus = "active" | "inactive" | "expired" | "unknown";

export type Job = {
  id: string;
  company_id: string;
  title: string;
  normalized_title: string | null;
  role_category: RoleCategory | null;
  description: string | null;
  location: string | null;
  remote_type: RemoteType | null;
  experience_min: number | null;
  experience_max: number | null;
  salary_min: number | string | null;
  salary_max: number | string | null;
  salary_currency: string | null;
  job_url: string | null;
  source_platform: string | null;
  status: JobStatus;
  first_seen_at: string | null;
  last_seen_at: string | null;
  created_at: string;
  updated_at: string | null;
};

export type JobCreateInput = {
  title: string;
  role_category?: RoleCategory | null;
  description?: string | null;
  location?: string | null;
  remote_type?: RemoteType | null;
  experience_min?: number | null;
  experience_max?: number | null;
  salary_min?: number | null;
  salary_max?: number | null;
  salary_currency?: string | null;
  job_url: string;
  source_platform?: string | null;
  status?: JobStatus;
  first_seen_at?: string | null;
  last_seen_at?: string | null;
};

export type JobUpdateInput = Partial<JobCreateInput>;

export type ListJobsParams = {
  page?: number;
  page_size?: number;
  company_id?: string;
  role_category?: RoleCategory;
  remote_type?: RemoteType;
  status?: JobStatus;
  search?: string;
};

export type ListCompanyJobsParams = {
  page?: number;
  page_size?: number;
  role_category?: RoleCategory;
  remote_type?: RemoteType;
  status?: JobStatus;
  search?: string;
};
