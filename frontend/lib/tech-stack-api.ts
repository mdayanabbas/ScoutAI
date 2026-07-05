import { api } from "@/lib/api";
import type { MessageResponse } from "@/types/common";
import type {
  TechStackItem,
  TechStackItemCreateInput,
  TechStackItemUpdateInput,
} from "@/types/tech-stack";

export function listCompanyTechStack(companyId: string) {
  return api.get<TechStackItem[]>(`/companies/${companyId}/tech-stack`);
}

export function createCompanyTechStackItem(
  companyId: string,
  data: TechStackItemCreateInput,
) {
  return api.post<TechStackItem>(`/companies/${companyId}/tech-stack`, data);
}

export function updateTechStackItem(
  itemId: string,
  data: TechStackItemUpdateInput,
) {
  return api.patch<TechStackItem>(`/tech-stack/${itemId}`, data);
}

export function deleteTechStackItem(itemId: string) {
  return api.delete<MessageResponse>(`/tech-stack/${itemId}`);
}
