import { useQuery } from "@tanstack/react-query";

import {
  getDashboard,
  getDashboardActivity,
  getDashboardSummary,
} from "@/lib/dashboard-api";

export const dashboardKeys = {
  all: ["dashboard"] as const,
  overview: () => [...dashboardKeys.all, "overview"] as const,
  summary: () => [...dashboardKeys.all, "summary"] as const,
  activity: (limit?: number) =>
    [...dashboardKeys.all, "activity", { limit }] as const,
};

export function useDashboardSummary() {
  return useQuery({
    queryKey: dashboardKeys.summary(),
    queryFn: getDashboardSummary,
  });
}

export function useDashboardActivity(limit?: number) {
  return useQuery({
    queryKey: dashboardKeys.activity(limit),
    queryFn: () => getDashboardActivity(limit),
  });
}

export function useDashboard() {
  return useQuery({
    queryKey: dashboardKeys.overview(),
    queryFn: getDashboard,
  });
}
