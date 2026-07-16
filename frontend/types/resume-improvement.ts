export type ResumeImprovementRequest = {
  update_decision?: boolean;
  include_section_suggestions?: boolean;
  include_bullet_suggestions?: boolean;
  include_skill_gap_suggestions?: boolean;
  include_project_reordering?: boolean;
  include_remote_fit_suggestions?: boolean;
};

export type ResumeImprovementItem = {
  category?: string | null;
  suggestion?: string | null;
  reason?: string | null;
  priority?: string | null;
  evidence?: string | null;
  caution?: string | null;
};

export type ResumeSectionSuggestion = {
  section?: string | null;
  action?: string | null;
  suggestion?: string | null;
  reason?: string | null;
  priority?: string | null;
};

export type ResumeBulletSuggestion = {
  target_section?: string | null;
  bullet_template?: string | null;
  supported_by_resume?: boolean | null;
  supporting_evidence?: string | null;
  caution?: string | null;
};

export type ResumeSkillGapSuggestion = {
  skill?: string | null;
  found_in_resume?: boolean | null;
  required_or_preferred?: string | null;
  suggestion?: string | null;
  caution?: string | null;
};

export type ResumeImprovementResponse = {
  job_id: string;
  decision_id?: string | null;
  resume_id?: string | null;
  resume_used?: boolean;
  company_name?: string | null;
  title?: string | null;
  match_tier?: string | null;
  total_score?: number | null;
  remote_eligibility?: string | null;
  improvement_summary?: string | null;
  section_suggestions?: ResumeSectionSuggestion[] | null;
  bullet_suggestions?: ResumeBulletSuggestion[] | null;
  skill_gap_suggestions?: ResumeSkillGapSuggestion[] | null;
  project_reordering_suggestions?: ResumeImprovementItem[] | null;
  remote_fit_suggestions?: ResumeImprovementItem[] | null;
  risks?: ResumeImprovementItem[] | null;
  suggested_next_action?: string | null;
  generated_at?: string | null;
};
