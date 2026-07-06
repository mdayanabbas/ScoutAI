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

export type AgentStep = {
  id: string;
  agent_run_id: string;
  step_name: string;
  step_order: number | null;
  input_payload: Record<string, unknown> | null;
  output_payload: Record<string, unknown> | null;
  error_message: string | null;
  latency_ms: number | null;
  created_at: string;
  updated_at: string | null;
};

export type AgentRunCreateInput = {
  company_id?: string | null;
  job_id?: string | null;
  agent_name: string;
  model_provider?: string | null;
  model_name?: string | null;
  input_summary?: string | null;
  metadata?: Record<string, unknown> | null;
};

export type AgentRunMarkSuccessInput = {
  output_summary?: string | null;
  latency_ms?: number | null;
};

export type AgentRunMarkFailedInput = {
  error_message: string;
  latency_ms?: number | null;
};

export type AgentStepCreateInput = {
  step_name: string;
  step_order: number;
  input_payload?: Record<string, unknown> | null;
  output_payload?: Record<string, unknown> | null;
  error_message?: string | null;
  latency_ms?: number | null;
};

export type AgentStepUpdateInput = Partial<AgentStepCreateInput>;

export type ListAgentRunsParams = {
  page?: number;
  page_size?: number;
  agent_name?: string;
  status?: AgentRunStatus;
  company_id?: string;
  job_id?: string;
};
