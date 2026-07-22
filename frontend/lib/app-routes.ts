export const APP_ROUTES = {
  commandCenter: "/applications/command-center",
  analytics: "/applications/analytics",
  followUps: "/applications/follow-ups",
  discovery: "/discovery/control-center",
  recommendedJobs: "/recommendations",
  pipeline: "/jobs/pipeline",
  trackedJobs: "/jobs/tracked",
  companyWatchlist: "/companies/watchlist",
  resume: "/profile/resume",
  jobs: "/jobs",
  companies: "/companies",
  dashboard: "/dashboard",
} as const;

export type AppRouteKey = keyof typeof APP_ROUTES;

export const primaryAppNavigation: Array<{ key: AppRouteKey; label: string; shortLabel?: string; icon: string }> = [
  { key: "commandCenter", label: "Command Center", icon: "K" },
  { key: "discovery", label: "Daily Scout", shortLabel: "Discovery", icon: "F" },
  { key: "recommendedJobs", label: "Recommended Jobs", shortLabel: "Recommendations", icon: "R" },
  { key: "pipeline", label: "Pipeline", icon: "B" },
  { key: "followUps", label: "Follow-ups", icon: "U" },
  { key: "analytics", label: "Analytics", icon: "Y" },
  { key: "companyWatchlist", label: "Company Watchlist", shortLabel: "Watchlist", icon: "W" },
  { key: "resume", label: "Resume", icon: "V" },
];

export function appRoute(key: AppRouteKey) {
  return APP_ROUTES[key];
}

export function routeIsActive(pathname: string, href: string) {
  return pathname === href || pathname.startsWith(`${href}/`);
}
