import type { ReactNode } from "react";
import Link from "next/link";

import { Sidebar } from "@/components/layout/Sidebar";
import { Topbar } from "@/components/layout/Topbar";
import { APP_ROUTES } from "@/lib/app-routes";

export function AppShell({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-screen bg-[#f7f8fb] text-[#171923]">
      <Sidebar />
      <div className="min-h-screen lg:pl-64">
        <Topbar />
        <main className="mx-auto w-full max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
          {children}
        </main>
        <footer className="mx-auto w-full max-w-7xl px-4 pb-6 text-xs text-[#667085] sm:px-6 lg:px-8">
          <div className="flex flex-wrap gap-3 border-t border-[#d9dee8] pt-4">
            <span>ScoutAI local build</span>
            <Link href={APP_ROUTES.commandCenter} className="font-medium text-[#475467]">Command Center</Link>
            <Link href={APP_ROUTES.discovery} className="font-medium text-[#475467]">Discovery</Link>
            <Link href={APP_ROUTES.pipeline} className="font-medium text-[#475467]">Pipeline</Link>
          </div>
        </footer>
      </div>
    </div>
  );
}
