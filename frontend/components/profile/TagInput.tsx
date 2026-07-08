"use client";

import { KeyboardEvent, useState } from "react";

export function TagInput({
  label,
  values,
  onChange,
  suggestions = [],
  placeholder = "Add item",
  error,
}: {
  label: string;
  values: string[];
  onChange: (values: string[]) => void;
  suggestions?: string[];
  placeholder?: string;
  error?: string;
}) {
  const [draft, setDraft] = useState("");

  function addTag(value: string) {
    const trimmed = value.trim();
    if (!trimmed) {
      return;
    }

    const exists = values.some(
      (item) => item.toLowerCase() === trimmed.toLowerCase(),
    );
    if (!exists) {
      onChange([...values, trimmed]);
    }
    setDraft("");
  }

  function removeTag(value: string) {
    onChange(values.filter((item) => item !== value));
  }

  function handleKeyDown(event: KeyboardEvent<HTMLInputElement>) {
    if (event.key === "Enter") {
      event.preventDefault();
      addTag(draft);
    }
  }

  return (
    <div>
      <div className="mb-1.5 flex items-center justify-between gap-3">
        <label className="text-sm font-medium text-[#344054]">{label}</label>
        {suggestions.length > 0 ? (
          <span className="text-xs text-[#667085]">Suggestions below</span>
        ) : null}
      </div>
      <div className="flex gap-2">
        <input
          value={draft}
          onChange={(event) => setDraft(event.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          className="min-w-0 flex-1 rounded border border-[#c8ced8] px-3 py-2 text-sm outline-none focus:border-[#172033]"
        />
        <button
          type="button"
          onClick={() => addTag(draft)}
          className="rounded border border-[#c8ced8] bg-white px-3 py-2 text-sm font-medium text-[#344054] hover:bg-[#f8fafc]"
        >
          Add
        </button>
      </div>
      {error ? <p className="mt-1 text-xs text-[#b42318]">{error}</p> : null}
      {values.length > 0 ? (
        <div className="mt-3 flex flex-wrap gap-2">
          {values.map((value) => (
            <span
              key={value}
              className="inline-flex items-center gap-1 rounded-full border border-[#d9dee8] bg-[#f8fafc] px-2.5 py-1 text-xs font-medium text-[#344054]"
            >
              {value}
              <button
                type="button"
                onClick={() => removeTag(value)}
                className="text-[#667085] hover:text-[#b42318]"
                aria-label={`Remove ${value}`}
              >
                x
              </button>
            </span>
          ))}
        </div>
      ) : null}
      {suggestions.length > 0 ? (
        <div className="mt-3 flex flex-wrap gap-2">
          {suggestions.map((suggestion) => {
            const selected = values.some(
              (item) => item.toLowerCase() === suggestion.toLowerCase(),
            );
            return (
              <button
                key={suggestion}
                type="button"
                onClick={() => addTag(suggestion)}
                disabled={selected}
                className="rounded border border-[#d9dee8] bg-white px-2.5 py-1 text-xs text-[#475467] hover:bg-[#f8fafc] disabled:cursor-not-allowed disabled:opacity-50"
              >
                {suggestion}
              </button>
            );
          })}
        </div>
      ) : null}
    </div>
  );
}
