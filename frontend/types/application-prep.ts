export type ApplicationPrepRequest = {
  update_decision?: boolean;
  include_cold_dm_angle?: boolean;
  include_resume_focus?: boolean;
  include_checklist?: boolean;
};

export type ApplicationPrepListItem = {
  label?: string;
  value?: string;
  reason?: string;
};

export type ApplicationPrepResponse = {
  job_id: string;
  decision_id?: string | null;
  company_name?: string | null;
  title?: string | null;
  match_tier?: string | null;
  total_score?: number | null;
  remote_eligibility?: string | null;
  fit_summary?: string | null;
  resume_focus_points?: ApplicationPrepListItem[];
  project_talking_points?: ApplicationPrepListItem[];
  concerns?: ApplicationPrepListItem[];
  missing_information?: string[];
  suggested_next_action?: string | null;
  cold_dm_angle?: string | null;
  application_checklist?: ApplicationPrepListItem[];
  generated_at?: string;
};
