export type DashboardSummary = {
  total_companies: number;
  total_jobs: number;
  active_jobs: number;
  remote_jobs: number;
  companies_added_today: number;
  jobs_added_today: number;
  recent_crawl_runs: number;
  successful_crawl_runs: number;
  failed_crawl_runs: number;
  recent_agent_runs: number;
  successful_agent_runs: number;
  failed_agent_runs: number;
};

export type RecentActivityItem = {
  type: string;
  title: string;
  description: string | null;
  entity_id: string;
  created_at: string;
};

export type DashboardResponse = {
  summary: DashboardSummary;
  recent_activity: RecentActivityItem[];
};
