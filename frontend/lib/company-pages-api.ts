import { api } from "@/lib/api";
import type { PaginatedResponse } from "@/types/common";
import type {
  CompanyPage,
  CompanyPageCreateInput,
  CompanyPageUpdateInput,
  ListCompanyPagesParams,
} from "@/types/company-page";
import type { MessageResponse } from "@/types/common";

export function listCompanyPages(
  companyId: string,
  params: ListCompanyPagesParams = {},
) {
  return api.get<PaginatedResponse<CompanyPage>>(
    `/companies/${companyId}/pages`,
    params,
  );
}

export function getCompanyPage(pageId: string) {
  return api.get<CompanyPage>(`/company-pages/${pageId}`);
}

export function createCompanyPage(
  companyId: string,
  data: CompanyPageCreateInput,
) {
  return api.post<CompanyPage>(`/companies/${companyId}/pages`, data);
}

export function updateCompanyPage(
  pageId: string,
  data: CompanyPageUpdateInput,
) {
  return api.patch<CompanyPage>(`/company-pages/${pageId}`, data);
}

export function deleteCompanyPage(pageId: string) {
  return api.delete<MessageResponse>(`/company-pages/${pageId}`);
}
