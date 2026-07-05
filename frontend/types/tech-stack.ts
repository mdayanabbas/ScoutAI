export type TechStackCategory =
  | "programming_language"
  | "backend_framework"
  | "frontend_framework"
  | "database"
  | "cloud"
  | "infrastructure"
  | "devops"
  | "ai_ml"
  | "vector_database"
  | "monitoring"
  | "testing"
  | "other";

export type TechStackSource =
  | "manual"
  | "job_description"
  | "company_website"
  | "careers_page"
  | "engineering_blog"
  | "github"
  | "agent"
  | "other";

export type TechStackItem = {
  id: string;
  company_id: string;
  name: string;
  category: TechStackCategory | string | null;
  source: TechStackSource | string | null;
  confidence: number;
  created_at: string;
  updated_at: string | null;
};

export type TechStackItemCreateInput = {
  name: string;
  category?: TechStackCategory | string | null;
  source?: TechStackSource | string | null;
  confidence?: number;
};

export type TechStackItemUpdateInput = Partial<TechStackItemCreateInput>;
