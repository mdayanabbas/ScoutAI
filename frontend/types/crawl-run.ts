export type CrawlStatus = "pending" | "running" | "success" | "failed" | "skipped";

export type CrawlRun = {
  id: string;
  company_id: string;
  status: CrawlStatus;
  started_at: string | null;
  finished_at: string | null;
  pages_found: number | null;
  pages_crawled: number | null;
  error_message: string | null;
  metadata: Record<string, unknown> | null;
  created_at: string;
  updated_at: string | null;
};

export type CrawlRunMarkSuccessInput = {
  pages_found?: number | null;
  pages_crawled?: number | null;
};

export type CrawlRunMarkFailedInput = {
  error_message: string;
};

export type ListCrawlRunsParams = {
  page?: number;
  page_size?: number;
  status?: CrawlStatus;
};

export type ListCompanyCrawlRunsParams = {
  page?: number;
  page_size?: number;
};
