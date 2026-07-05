export type TechStackItem = {
  id: string;
  company_id: string;
  name: string;
  category: string | null;
  source: string | null;
  confidence: number;
  created_at: string;
  updated_at: string | null;
};
