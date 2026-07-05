import { api } from "@/lib/api";
import type {
  DashboardResponse,
  DashboardSummary,
  RecentActivityItem,
} from "@/types/dashboard";

export function getDashboardSummary() {
  return api.get<DashboardSummary>("/dashboard/summary");
}

export function getDashboardActivity(limit?: number) {
  return api.get<RecentActivityItem[]>("/dashboard/activity", { limit });
}

export function getDashboard() {
  return api.get<DashboardResponse>("/dashboard");
}
