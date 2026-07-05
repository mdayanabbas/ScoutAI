import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  createCompanyPage,
  deleteCompanyPage,
  getCompanyPage,
  listCompanyPages,
  updateCompanyPage,
} from "@/lib/company-pages-api";
import { companyKeys } from "@/hooks/use-companies";
import { dashboardKeys } from "@/hooks/use-dashboard";
import type {
  CompanyPageCreateInput,
  CompanyPageUpdateInput,
  ListCompanyPagesParams,
} from "@/types/company-page";

export const companyPageKeys = {
  all: ["company-pages"] as const,
  company: (companyId: string) =>
    [...companyPageKeys.all, "company", companyId] as const,
  detail: (pageId: string) => [...companyPageKeys.all, "detail", pageId] as const,
};

export function useCompanyPages(
  companyId: string,
  params: ListCompanyPagesParams = { page: 1, page_size: 20 },
) {
  return useQuery({
    queryKey: [...companyPageKeys.company(companyId), params],
    queryFn: () => listCompanyPages(companyId, params),
    enabled: Boolean(companyId),
  });
}

export function useCompanyPage(pageId: string | null) {
  return useQuery({
    queryKey: companyPageKeys.detail(pageId ?? ""),
    queryFn: () => getCompanyPage(pageId ?? ""),
    enabled: Boolean(pageId),
  });
}

export function useCreateCompanyPage(companyId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: CompanyPageCreateInput) =>
      createCompanyPage(companyId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: companyPageKeys.company(companyId),
      });
      queryClient.invalidateQueries({ queryKey: companyKeys.detail(companyId) });
      queryClient.invalidateQueries({ queryKey: dashboardKeys.all });
    },
  });
}

export function useUpdateCompanyPage() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      pageId,
      companyId,
      data,
    }: {
      pageId: string;
      companyId: string;
      data: CompanyPageUpdateInput;
    }) => updateCompanyPage(pageId, data),
    onSuccess: (page, variables) => {
      queryClient.invalidateQueries({
        queryKey: companyPageKeys.company(variables.companyId),
      });
      queryClient.invalidateQueries({ queryKey: companyPageKeys.detail(page.id) });
      queryClient.invalidateQueries({
        queryKey: companyKeys.detail(variables.companyId),
      });
      queryClient.invalidateQueries({ queryKey: dashboardKeys.all });
    },
  });
}

export function useDeleteCompanyPage(companyId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (pageId: string) => deleteCompanyPage(pageId),
    onSuccess: (_response, pageId) => {
      queryClient.invalidateQueries({
        queryKey: companyPageKeys.company(companyId),
      });
      queryClient.invalidateQueries({ queryKey: companyPageKeys.detail(pageId) });
      queryClient.invalidateQueries({ queryKey: companyKeys.detail(companyId) });
      queryClient.invalidateQueries({ queryKey: dashboardKeys.all });
    },
  });
}
