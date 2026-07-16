export type ResumeParseStatus = "uploaded" | "parsed" | "failed" | string;

export type ResumeResponse = {
  id: string;
  user_profile_id?: string | null;
  filename?: string | null;
  original_filename?: string | null;
  content_type?: string | null;
  file_size_bytes?: number | null;
  is_active?: boolean;
  parse_status?: ResumeParseStatus;
  parse_error?: string | null;
  parsed_summary?: Record<string, unknown> | null;
  skills?: string[] | null;
  technologies?: string[] | null;
  projects?: Array<Record<string, unknown>> | null;
  experience?: Array<Record<string, unknown>> | null;
  education?: Array<Record<string, unknown>> | null;
  certifications?: Array<Record<string, unknown>> | null;
  links?: string[] | null;
  created_at?: string | null;
  updated_at?: string | null;
  parsed_at?: string | null;
};

export type ResumeListResponse = {
  items: ResumeResponse[];
  total: number;
  limit: number;
  offset: number;
};

export type ResumeUploadResponse = {
  resume: ResumeResponse;
  warnings?: string[];
};

export type ResumeActivateResponse = {
  resume_id: string;
  is_active: boolean;
  previous_active_resume_id?: string | null;
};

export type ResumeListParams = {
  limit?: number;
  offset?: number;
};
