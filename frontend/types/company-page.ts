export type PageType =
  | "homepage"
  | "about"
  | "careers"
  | "jobs"
  | "team"
  | "blog"
  | "engineering"
  | "docs"
  | "pricing"
  | "unknown";

export type CompanyPage = {
  id: string;
  company_id: string;
  url: string;
  page_type: PageType;
  title: string | null;
  html_hash: string | null;
  status_code: number | null;
  content_length: number | null;
  last_crawled_at: string | null;
  created_at: string;
  updated_at: string | null;
};

export type ListCompanyPagesParams = {
  page?: number;
  page_size?: number;
  page_type?: PageType;
};
