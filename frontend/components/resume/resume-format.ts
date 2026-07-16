import type { ResumeParseStatus } from "@/types/resume";

export function formatFileSize(value?: number | null) {
  if (!value) {
    return "0 B";
  }
  if (value < 1024) {
    return `${value} B`;
  }
  if (value < 1024 * 1024) {
    return `${(value / 1024).toFixed(1)} KB`;
  }
  return `${(value / (1024 * 1024)).toFixed(1)} MB`;
}

export function formatDate(value?: string | null) {
  if (!value) {
    return "Not yet";
  }
  return new Intl.DateTimeFormat("en", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

export function parseStatusLabel(value?: ResumeParseStatus | null) {
  return (
    {
      uploaded: "Uploaded",
      parsed: "Parsed",
      failed: "Parse Failed",
    }[value ?? ""] ?? "Unknown"
  );
}

export function parseStatusTone(value?: ResumeParseStatus | null) {
  if (value === "parsed") {
    return "border-[#bbf7d0] bg-[#f0fdf4] text-[#166534]";
  }
  if (value === "failed") {
    return "border-[#fecaca] bg-[#fff7f7] text-[#991b1b]";
  }
  return "border-[#fed7aa] bg-[#fff7ed] text-[#9a3412]";
}

export function stringFromUnknown(value: unknown) {
  if (typeof value === "string") {
    return value;
  }
  if (value && typeof value === "object") {
    const record = value as Record<string, unknown>;
    return String(record.title ?? record.name ?? record.text ?? JSON.stringify(record));
  }
  return String(value ?? "");
}
