import { api } from "@/lib/api";
import type { MessageResponse, PaginatedResponse } from "@/types/common";
import type {
  Company,
  CompanyCreate,
  CompanyUpdate,
  ListCompaniesParams,
} from "@/types/company";

export function listCompanies(params: ListCompaniesParams = {}) {
  return api.get<PaginatedResponse<Company>>("/companies", params);
}

export function getCompany(id: string) {
  return api.get<Company>(`/companies/${id}`);
}

export function createCompany(data: CompanyCreate) {
  return api.post<Company>("/companies", data);
}

export function updateCompany(id: string, data: CompanyUpdate) {
  return api.patch<Company>(`/companies/${id}`, data);
}

export function deleteCompany(id: string) {
  return api.delete<MessageResponse>(`/companies/${id}`);
}
