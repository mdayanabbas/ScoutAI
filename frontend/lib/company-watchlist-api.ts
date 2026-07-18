import { api } from "@/lib/api";
import type {
  CompanyWatchlistCreate,
  CompanyWatchlistJobsParams,
  CompanyWatchlistJobsResponse,
  CompanyWatchlistListResponse,
  CompanyWatchlistParams,
  CompanyWatchlistResponse,
  CompanyWatchlistStatsResponse,
  CompanyWatchlistUpdate,
} from "@/types/company-watchlist";

export function createCompanyWatchlistItem(payload: CompanyWatchlistCreate) {
  return api.post<CompanyWatchlistResponse>("/company-watchlist", payload);
}

export function fetchCompanyWatchlist(params: CompanyWatchlistParams = {}) {
  return api.get<CompanyWatchlistListResponse>("/company-watchlist", params);
}

export function fetchCompanyWatchlistStats() {
  return api.get<CompanyWatchlistStatsResponse>("/company-watchlist/stats");
}

export function fetchCompanyWatchlistItem(itemId: string) {
  return api.get<CompanyWatchlistResponse>(`/company-watchlist/${itemId}`);
}

export function updateCompanyWatchlistItem(itemId: string, payload: CompanyWatchlistUpdate) {
  return api.patch<CompanyWatchlistResponse>(`/company-watchlist/${itemId}`, payload);
}

export function archiveCompanyWatchlistItem(itemId: string) {
  return api.post<CompanyWatchlistResponse>(`/company-watchlist/${itemId}/archive`);
}

export function deleteCompanyWatchlistItem(itemId: string) {
  return api.delete<void>(`/company-watchlist/${itemId}`);
}

export function fetchCompanyWatchlistJobs(itemId: string, params: CompanyWatchlistJobsParams = {}) {
  return api.get<CompanyWatchlistJobsResponse>(`/company-watchlist/${itemId}/jobs`, params);
}

export function watchCompanyFromJob(jobId: string, payload: CompanyWatchlistCreate = {}) {
  return api.post<CompanyWatchlistResponse>(`/company-watchlist/from-job/${jobId}`, payload);
}
