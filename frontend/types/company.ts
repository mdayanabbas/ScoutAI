export type CompanyStage =
  | "unknown"
  | "pre_seed"
  | "seed"
  | "series_a"
  | "series_b"
  | "growth"
  | "public";

export type CompanySource =
  | "manual"
  | "yc"
  | "product_hunt"
  | "hacker_news"
  | "wellfound"
  | "company_website"
  | "rss"
  | "other";

export type Company = {
  id: string;
  name: string;
  website_url: string | null;
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

export type CompanyCreateInput = {
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

export type CompanyUpdateInput = Partial<CompanyCreateInput>;

export type CompanyCreate = CompanyCreateInput;
export type CompanyUpdate = CompanyUpdateInput;

export type ListCompaniesParams = {
  page?: number;
  page_size?: number;
  search?: string;
  source?: CompanySource;
  stage?: CompanyStage;
  is_active?: boolean;
};
