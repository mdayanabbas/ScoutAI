import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  createCompanyTechStackItem,
  deleteTechStackItem,
  listCompanyTechStack,
  updateTechStackItem,
} from "@/lib/tech-stack-api";
import { companyKeys } from "@/hooks/use-companies";
import type {
  TechStackItemCreateInput,
  TechStackItemUpdateInput,
} from "@/types/tech-stack";

export const techStackKeys = {
  all: ["company-tech-stack"] as const,
  company: (companyId: string) =>
    [...techStackKeys.all, "company", companyId] as const,
};

export function useCompanyTechStack(companyId: string) {
  return useQuery({
    queryKey: techStackKeys.company(companyId),
    queryFn: () => listCompanyTechStack(companyId),
    enabled: Boolean(companyId),
  });
}

export function useCreateTechStackItem(companyId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: TechStackItemCreateInput) =>
      createCompanyTechStackItem(companyId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: techStackKeys.company(companyId) });
      queryClient.invalidateQueries({ queryKey: companyKeys.detail(companyId) });
    },
  });
}

export function useUpdateTechStackItem(companyId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      itemId,
      data,
    }: {
      itemId: string;
      data: TechStackItemUpdateInput;
    }) => updateTechStackItem(itemId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: techStackKeys.company(companyId) });
      queryClient.invalidateQueries({ queryKey: companyKeys.detail(companyId) });
    },
  });
}

export function useDeleteTechStackItem(companyId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (itemId: string) => deleteTechStackItem(itemId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: techStackKeys.company(companyId) });
      queryClient.invalidateQueries({ queryKey: companyKeys.detail(companyId) });
    },
  });
}
