import { api } from "@/lib/api";
import type { TechStackItem } from "@/types/tech-stack";

export function listCompanyTechStack(companyId: string) {
  return api.get<TechStackItem[]>(`/companies/${companyId}/tech-stack`);
}
