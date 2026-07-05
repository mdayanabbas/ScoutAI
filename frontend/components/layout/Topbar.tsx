import Link from "next/link";

export function Topbar() {
  return (
    <header className="sticky top-0 z-20 border-b border-[#d9dee8] bg-white/95 backdrop-blur">
      <div className="mx-auto flex h-16 w-full max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
        <Link
          href="/dashboard"
          className="flex items-center gap-3 text-sm font-semibold lg:hidden"
        >
          <span className="grid h-8 w-8 place-items-center rounded bg-[#172033] text-white">
            S
          </span>
          ScoutAI
        </Link>
        <div className="hidden text-sm text-[#667085] lg:block">
          Company discovery workspace
        </div>
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
