export type CompanyStage =
  | "unknown"
  | "pre_seed"
  | "seed"
  | "series_a"
  | "series_b"
  | "series_c_plus"
  | "public"
  | string;

export type CompanySource =
  | "manual"
  | "wellfound"
  | "yc"
  | "linkedin"
  | "other"
  | string;

export type Company = {
  id: string;
  name: string;
  website_url: string;
  normalized_domain: string;
  description: string | null;
  country: string | null;
  city: string | null;
  stage: CompanyStage;
  source: CompanySource;
  employee_count_min: number | null;
  employee_count_max: number | null;
  founded_year: number | null;
  is_active: boolean;
  created_at: string;
  updated_at: string | null;
};

export type CompanyCreate = {
  name: string;
  website_url: string;
  description?: string | null;
  country?: string | null;
  city?: string | null;
  stage?: CompanyStage;
  source?: CompanySource;
  employee_count_min?: number | null;
  employee_count_max?: number | null;
  founded_year?: number | null;
  is_active?: boolean;
};

export type CompanyUpdate = Partial<CompanyCreate>;

export type ListCompaniesParams = {
  page?: number;
  page_size?: number;
  search?: string;
  source?: CompanySource;
  stage?: CompanyStage;
  is_active?: boolean;
};
