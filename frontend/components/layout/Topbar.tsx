"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { APP_ROUTES, primaryAppNavigation, routeIsActive } from "@/lib/app-routes";

export function Topbar() {
  const pathname = usePathname();
  return (
    <header className="sticky top-0 z-20 border-b border-[#d9dee8] bg-white/95 backdrop-blur">
      <div className="mx-auto flex min-h-16 w-full max-w-7xl flex-col gap-3 px-4 py-3 sm:px-6 lg:h-16 lg:flex-row lg:items-center lg:justify-between lg:gap-4 lg:px-8 lg:py-0">
        <Link
          href={APP_ROUTES.dashboard}
          className="flex items-center gap-3 text-sm font-semibold lg:hidden"
        >
          <span className="grid h-8 w-8 place-items-center rounded bg-[#172033] text-white">
            S
          </span>
          ScoutAI
        </Link>
        <div className="hidden text-sm text-[#667085] lg:block">
          ScoutAI local build
        </div>
        <nav className="flex gap-2 overflow-x-auto pb-1 lg:hidden" aria-label="Primary">
          {primaryAppNavigation.map((item) => {
            const href = APP_ROUTES[item.key];
            const active = routeIsActive(pathname, href);
            return (
              <Link
                key={item.key}
                href={href}
                className={`shrink-0 rounded px-2.5 py-1.5 text-xs font-medium ${active ? "bg-[#172033] text-white" : "border border-[#e4e7ec] text-[#475467]"}`}
              >
                {item.shortLabel ?? item.label}
              </Link>
            );
          })}
        </nav>
        <div className="flex items-center gap-3">
          <span className="hidden text-sm text-[#667085] sm:inline">
            Local backend
          </span>
          <span className="h-2.5 w-2.5 rounded-full bg-[#16a34a]" />
        </div>
      </div>
    </header>
  );
}
