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

export type ListCompanyCrawlRunsParams = {
  page?: number;
  page_size?: number;
};
