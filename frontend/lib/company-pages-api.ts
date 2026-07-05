import { api } from "@/lib/api";
import type { PaginatedResponse } from "@/types/common";
import type {
  CompanyPage,
  ListCompanyPagesParams,
} from "@/types/company-page";

export function listCompanyPages(
  companyId: string,
  params: ListCompanyPagesParams = {},
) {
  return api.get<PaginatedResponse<CompanyPage>>(
    `/companies/${companyId}/pages`,
    params,
  );
}
