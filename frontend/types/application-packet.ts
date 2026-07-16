export type ApplicationPacketRequest = {
  update_decision?: boolean;
  include_resume_bullets?: boolean;
  include_cover_note_outline?: boolean;
  include_cold_dm_outline?: boolean;
  include_checklist?: boolean;
  include_risk_review?: boolean;
};

export type ApplicationPacketItem = {
  label?: string | null;
  value?: string | null;
  reason?: string | null;
  severity?: string | null;
};

export type ApplicationPacketEvidenceItem = ApplicationPacketItem | string | Record<string, unknown>;

export type ApplicationPacketSection = {
  title?: string | null;
  items?: ApplicationPacketItem[] | null;
};

export type ApplicationPacketResponse = {
  job_id: string;
  decision_id?: string | null;
  company_name?: string | null;
  title?: string | null;
  role_category?: string | null;
  match_tier?: string | null;
  total_score?: number | null;
  remote_eligibility?: string | null;
  resume_id?: string | null;
  resume_used?: boolean;
  resume_match_summary?: string | null;
  resume_strengths?: ApplicationPacketEvidenceItem[] | null;
  resume_gaps?: ApplicationPacketEvidenceItem[] | null;
  resume_bullet_sources?: ApplicationPacketEvidenceItem[] | null;
  application_positioning?: string | null;
  resume_focus?: ApplicationPacketItem[] | null;
  resume_bullet_suggestions?: ApplicationPacketItem[] | null;
  project_evidence_to_use?: ApplicationPacketItem[] | null;
  cover_note_outline?: ApplicationPacketSection | null;
  cold_dm_outline?: ApplicationPacketSection | null;
  application_checklist?: ApplicationPacketItem[] | null;
  risks_to_verify?: ApplicationPacketItem[] | null;
  suggested_apply_plan?: ApplicationPacketItem[] | null;
  generated_at?: string | null;
};
