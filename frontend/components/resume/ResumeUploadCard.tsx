"use client";

import { useMemo, useState } from "react";

import { formatFileSize } from "@/components/resume/resume-format";

const allowedExtensions = [".pdf", ".docx", ".txt"];
const maxFileSize = 5 * 1024 * 1024;

export function ResumeUploadCard({
  pending,
  onUpload,
}: {
  pending: boolean;
  onUpload: (file: File, makeActive: boolean) => Promise<void> | void;
}) {
  const [file, setFile] = useState<File | null>(null);
  const [makeActive, setMakeActive] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const selected = useMemo(() => {
    if (!file) {
      return null;
    }
    return `${file.name} (${formatFileSize(file.size)})`;
  }, [file]);

  function chooseFile(nextFile: File | null) {
    setError(null);
    if (!nextFile) {
      setFile(null);
      return;
    }
    const validation = validateFile(nextFile);
    if (validation) {
      setFile(null);
      setError(validation);
      return;
    }
    setFile(nextFile);
  }

  async function submit() {
    if (!file) {
      setError("Choose a PDF, DOCX or TXT resume first.");
      return;
    }
    const validation = validateFile(file);
    if (validation) {
      setError(validation);
      return;
    }
    setError(null);
    await onUpload(file, makeActive);
    setFile(null);
  }

  return (
    <section className="rounded-md border border-[#d9dee8] bg-white p-5 shadow-sm">
      <h2 className="text-base font-semibold text-[#171923]">Upload Resume</h2>
      <p className="mt-1 text-sm text-[#667085]">
        Upload a PDF, DOCX or TXT file. ScoutAI parses it locally through your backend.
      </p>

      <label
        className="mt-4 flex cursor-pointer flex-col items-center justify-center rounded border border-dashed border-[#c8ced8] bg-[#f8fafc] px-4 py-8 text-center hover:bg-[#eef2f6]"
        onDragOver={(event) => event.preventDefault()}
        onDrop={(event) => {
          event.preventDefault();
          chooseFile(event.dataTransfer.files.item(0));
        }}
      >
        <span className="text-sm font-medium text-[#344054]">
          Drop resume here or choose file
        </span>
        <span className="mt-1 text-xs text-[#667085]">PDF, DOCX, TXT up to 5 MB</span>
        <input
          type="file"
          accept=".pdf,.docx,.txt"
          className="sr-only"
          onChange={(event) => chooseFile(event.target.files?.item(0) ?? null)}
        />
      </label>

      {selected ? (
        <p className="mt-3 rounded border border-[#d9dee8] bg-[#fcfcfd] px-3 py-2 text-sm text-[#344054]">
          {selected}
        </p>
      ) : null}

      <label className="mt-3 flex items-center gap-2 text-sm text-[#344054]">
        <input
          type="checkbox"
          checked={makeActive}
          onChange={(event) => setMakeActive(event.target.checked)}
          className="h-4 w-4 rounded border-[#c8ced8]"
        />
        Make active resume
      </label>

      {error ? (
        <p className="mt-3 rounded border border-[#fecaca] bg-[#fff7f7] px-3 py-2 text-sm text-[#991b1b]">
          {error}
        </p>
      ) : null}

      <button
        type="button"
        onClick={submit}
        disabled={pending || !file}
        className="mt-4 rounded bg-[#172033] px-3 py-2 text-sm font-medium text-white hover:bg-[#0f1728] disabled:cursor-not-allowed disabled:opacity-60"
      >
        {pending ? "Uploading and parsing resume..." : "Upload Resume"}
      </button>
    </section>
  );
}

function validateFile(file: File) {
  const lower = file.name.toLowerCase();
  if (file.size <= 0) {
    return "Resume file is empty.";
  }
  if (file.size > maxFileSize) {
    return "Resume file must be 5 MB or smaller.";
  }
  if (!allowedExtensions.some((extension) => lower.endsWith(extension))) {
    return "Unsupported resume type. Use PDF, DOCX or TXT.";
  }
  return null;
}
