"use client";

import Link from "next/link";
import { useState } from "react";

import { ApiError } from "@/lib/api";
import { watchCompanyFromJob } from "@/lib/company-watchlist-api";
import type { CompanyWatchlistCreate } from "@/types/company-watchlist";

export function WatchCompanyButton({
  jobId,
  payload,
  className = "rounded border border-[#0f766e] bg-white px-3 py-2 text-sm font-medium text-[#0f766e] hover:bg-[#f0fdfa] disabled:cursor-not-allowed disabled:opacity-60",
}: {
  jobId: string;
  payload?: CompanyWatchlistCreate;
  className?: string;
}) {
  const [pending, setPending] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [watched, setWatched] = useState(false);

  async function watch() {
    setPending(true);
    setMessage(null);
    try {
      await watchCompanyFromJob(jobId, payload ?? {});
      setWatched(true);
      setMessage("Company watched.");
    } catch (error) {
      if (error instanceof ApiError && error.status === 409) {
        setWatched(true);
        setMessage("Company is already on your watchlist.");
      } else {
        setMessage(error instanceof Error ? error.message : "Could not watch company.");
      }
    } finally {
      setPending(false);
    }
  }

  return (
    <div className="flex flex-col items-start gap-1">
      <button type="button" disabled={pending || watched} onClick={watch} className={className}>
        {pending ? "Watching..." : watched ? "Company watched" : "Watch Company"}
      </button>
      {message ? (
        <div className="text-xs text-[#475467]">
          {message}{" "}
          {watched ? (
            <Link href="/companies/watchlist" className="font-medium text-[#175cd3] hover:underline">
              View Watchlist
            </Link>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
