import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  createCompany,
  deleteCompany,
  getCompany,
  listCompanies,
  updateCompany,
} from "@/lib/companies-api";
import { dashboardKeys } from "@/hooks/use-dashboard";
import type {
  CompanyCreate,
  CompanyUpdate,
  ListCompaniesParams,
} from "@/types/company";

export const companyKeys = {
  all: ["companies"] as const,
  lists: () => [...companyKeys.all, "list"] as const,
  list: (params: ListCompaniesParams) =>
    [...companyKeys.lists(), params] as const,
  detail: (id: string) => [...companyKeys.all, "detail", id] as const,
};

export function useCompanies(params: ListCompaniesParams = {}) {
  return useQuery({
    queryKey: companyKeys.list(params),
    queryFn: () => listCompanies(params),
  });
}

export function useCompany(id: string) {
  return useQuery({
    queryKey: companyKeys.detail(id),
    queryFn: () => getCompany(id),
    enabled: Boolean(id),
  });
}

export function useCreateCompany() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: CompanyCreate) => createCompany(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: companyKeys.lists() });
      queryClient.invalidateQueries({ queryKey: dashboardKeys.all });
    },
  });
}

export function useUpdateCompany() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: CompanyUpdate }) =>
      updateCompany(id, data),
    onSuccess: (company) => {
      queryClient.invalidateQueries({ queryKey: companyKeys.lists() });
      queryClient.invalidateQueries({ queryKey: companyKeys.detail(company.id) });
    },
  });
}

export function useDeleteCompany() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => deleteCompany(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: companyKeys.lists() });
    },
  });
}
