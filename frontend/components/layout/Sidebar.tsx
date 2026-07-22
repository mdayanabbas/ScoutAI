"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { APP_ROUTES, primaryAppNavigation, routeIsActive } from "@/lib/app-routes";

const navigation = [
  { name: "Dashboard", href: APP_ROUTES.dashboard, icon: "D" },
  ...primaryAppNavigation.map((item) => ({
    name: item.shortLabel ?? item.label,
    href: APP_ROUTES[item.key],
    icon: item.icon,
  })),
  { name: "Companies", href: APP_ROUTES.companies, icon: "C" },
  { name: "Jobs", href: APP_ROUTES.jobs, icon: "J" },
  { name: "Tracked Jobs", href: APP_ROUTES.trackedJobs, icon: "T" },
  { name: "Outreach", href: "/outreach", icon: "O" },
  { name: "CRM", href: "/crm", icon: "M" },
  { name: "Profile", href: "/profile", icon: "P" },
  { name: "Agent Runs", href: "/agent-runs", icon: "A" },
];

export function Sidebar() {
  const pathname = usePathname();
  const activeHref = navigation
    .filter((item) => routeIsActive(pathname, item.href))
    .sort((a, b) => b.href.length - a.href.length)[0]?.href;

  return (
    <aside className="hidden fixed inset-y-0 left-0 z-30 w-64 border-r border-[#d9dee8] bg-white lg:block">
      <div className="flex h-16 items-center border-b border-[#d9dee8] px-6">
        <Link href="/dashboard" className="flex items-center gap-3">
          <span className="grid h-8 w-8 place-items-center rounded bg-[#172033] text-sm font-semibold text-white">
            S
          </span>
          <span className="text-base font-semibold tracking-normal">ScoutAI</span>
        </Link>
      </div>
      <nav className="space-y-1 px-3 py-4">
        {navigation.map((item) => {
          const active = activeHref === item.href;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={[
                "flex h-10 items-center gap-3 rounded px-3 text-sm transition-colors",
                active
                  ? "bg-[#172033] font-medium text-white"
                  : "text-[#475467] hover:bg-[#eef2f6] hover:text-[#171923]",
              ].join(" ")}
            >
              <span className="w-5 text-center text-base leading-none">
                {item.icon}
              </span>
              <span>{item.name}</span>
            </Link>
          );
        })}
      </nav>
    </aside>
  );
}
