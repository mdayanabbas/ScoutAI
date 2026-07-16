export type JobDecisionStatus =
  | "saved"
  | "interested"
  | "applied"
  | "skipped"
  | "not_interested"
  | "needs_custom_resume"
  | "needs_cold_dm"
  | "interviewing"
  | "rejected"
  | "offer"
  | "archived"
  | string;

export type JobDecisionPriority = "low" | "medium" | "high" | "urgent" | string;

export type JobApplicationDecisionResponse = {
  id: string;
  job_id: string;
  user_profile_id?: string | null;
  decision_status?: JobDecisionStatus;
  status?: JobDecisionStatus;
  priority?: JobDecisionPriority | null;
  applied_at?: string | null;
  saved_at?: string | null;
  skipped_at?: string | null;
  archived_at?: string | null;
  last_status_changed_at?: string | null;
  decided_at?: string | null;
  notes?: string | null;
  fit_summary?: string | null;
  concerns?: string | null;
  next_action?: string | null;
  next_action_due_at?: string | null;
  source_snapshot?: Record<string, unknown> | null;
  match_snapshot?: Record<string, unknown> | null;
  created_at?: string;
  updated_at?: string | null;
};

export type JobDecisionListItem = JobApplicationDecisionResponse & {
  company_id?: string | null;
  company_name?: string | null;
  title?: string | null;
  job_title?: string | null;
  remote_eligibility?: string | null;
  match_tier?: string | null;
  total_score?: number | null;
  eligibility_reason?: string | null;
  salary_min?: number | string | null;
  salary_max?: number | string | null;
  salary_currency?: string | null;
  job_url?: string | null;
  apply_url?: string | null;
};

export type JobDecisionListResponse = {
  items: JobDecisionListItem[];
  total: number;
  limit: number;
  offset: number;
};

export type JobDecisionStatusCounts = {
  total?: number;
  saved?: number;
  interested?: number;
  applied?: number;
  skipped?: number;
  not_interested?: number;
  needs_custom_resume?: number;
  needs_cold_dm?: number;
  interviewing?: number;
  rejected?: number;
  offer?: number;
  archived?: number;
};

export type JobDecisionPayload = {
  decision_status?: JobDecisionStatus;
  priority?: JobDecisionPriority;
  notes?: string | null;
  fit_summary?: string | null;
  concerns?: string | null;
  next_action?: string | null;
  next_action_due_at?: string | null;
};

export type JobDecisionListParams = {
  decision_status?: JobDecisionStatus;
  status?: JobDecisionStatus;
  priority?: JobDecisionPriority;
  order_by?: string;
  include_archived?: boolean;
  limit?: number;
  offset?: number;
};
