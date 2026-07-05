export type AgentRunStatus = "pending" | "running" | "success" | "failed";

export type AgentRun = {
  id: string;
  company_id: string | null;
  job_id: string | null;
  agent_name: string;
  status: AgentRunStatus;
  model_provider: string | null;
  model_name: string | null;
  input_summary: string | null;
  output_summary: string | null;
  error_message: string | null;
  latency_ms: number | null;
  started_at: string | null;
  finished_at: string | null;
  metadata: Record<string, unknown> | null;
  created_at: string;
  updated_at: string | null;
};

export type ListAgentRunsParams = {
  page?: number;
  page_size?: number;
  agent_name?: string;
  status?: AgentRunStatus;
  company_id?: string;
  job_id?: string;
};
