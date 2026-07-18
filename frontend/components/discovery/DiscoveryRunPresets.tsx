"use client";

import { useMemo, useState } from "react";
import type { ReactNode } from "react";

import { sourceLabels, type DiscoveryOptionsState } from "@/components/discovery/DiscoverySourceSelector";
import {
  materializePresetPayload,
  presetNeedsConfiguration,
  type DiscoveryRunPreset,
  type DiscoveryRunPresetCategory,
} from "@/lib/discovery-presets";
import type { SourceQualityAdvisorItem } from "@/lib/source-quality-advisor";
import type { RemoteJobDiscoveryRunRequest } from "@/types/discovery";

export type PresetRunSessionItem = {
  presetId: string;
  presetName: string;
  startedAt: string;
  status: string;
  duration: number | null;
  sources: string[];
  jobsScored: number;
  warningsCount: number;
};

const categories: DiscoveryRunPresetCategory[] = [
  "daily",
  "startup_signals",
  "remote_jobs",
  "aggressive",
  "custom",
];

export function DiscoveryRunPresets({
  presets,
  advisors,
  options,
  selectedSources,
  sessionRuns,
  running,
  message,
  onRunPreset,
  onApplyPreset,
  onSaveCurrentPreset,
  onUpdatePreset,
  onDuplicatePreset,
  onDeletePreset,
}: {
  presets: DiscoveryRunPreset[];
  advisors: SourceQualityAdvisorItem[];
  options: DiscoveryOptionsState;
  selectedSources: string[];
  sessionRuns: PresetRunSessionItem[];
  running: boolean;
  message: string | null;
  onRunPreset: (preset: DiscoveryRunPreset) => void;
  onApplyPreset: (preset: DiscoveryRunPreset) => void;
  onSaveCurrentPreset: (data: PresetFormData) => void;
  onUpdatePreset: (preset: DiscoveryRunPreset, data: PresetFormData) => void;
  onDuplicatePreset: (preset: DiscoveryRunPreset) => void;
  onDeletePreset: (preset: DiscoveryRunPreset) => void;
}) {
  const [previewPreset, setPreviewPreset] = useState<DiscoveryRunPreset | null>(null);
  const [saving, setSaving] = useState(false);
  const [editingPreset, setEditingPreset] = useState<DiscoveryRunPreset | null>(null);
  const recommendedPreset = useMemo(
    () => recommendedPresetName(advisors, presets),
    [advisors, presets],
  );

  return (
    <section className="mb-5 rounded-md border border-[#d9dee8] bg-white p-5">
      <div className="mb-5 flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <h2 className="text-base font-semibold text-[#171923]">Run Presets</h2>
          <p className="mt-1 text-sm text-[#667085]">
            Save and reuse common discovery source configurations.
          </p>
        </div>
        <button
          type="button"
          onClick={() => setSaving(true)}
          className="self-start rounded bg-[#172033] px-3 py-2 text-sm font-medium text-white hover:bg-[#0f1728]"
        >
          Save Current Selection as Preset
        </button>
      </div>

      {recommendedPreset ? (
        <div className="mb-4 rounded border border-[#bfdbfe] bg-[#eff6ff] p-3 text-sm text-[#1d4ed8]">
          Recommended Preset: <span className="font-semibold">{recommendedPreset}</span>
        </div>
      ) : null}
      {message ? <p className="mb-4 text-sm text-[#175cd3]">{message}</p> : null}

      <div className="grid gap-4 xl:grid-cols-2">
        {presets.map((preset) => (
          <PresetCard
            key={preset.id}
            preset={preset}
            options={options}
            running={running}
            onRun={() => onRunPreset(preset)}
            onPreview={() => setPreviewPreset(preset)}
            onApply={() => onApplyPreset(preset)}
            onDuplicate={() => onDuplicatePreset(preset)}
            onEdit={() => setEditingPreset(preset)}
            onDelete={() => onDeletePreset(preset)}
          />
        ))}
      </div>

      <PresetRunsThisSession runs={sessionRuns} />

      {previewPreset ? (
        <PresetPayloadPreview
          preset={previewPreset}
          payload={materializePresetPayload(previewPreset, options)}
          onClose={() => setPreviewPreset(null)}
          onRun={() => {
            setPreviewPreset(null);
            onRunPreset(previewPreset);
          }}
        />
      ) : null}

      {saving ? (
        <PresetFormModal
          title="Save Current Selection"
          initial={{
            name: "",
            description: "",
            category: "custom",
            payloadText: JSON.stringify(currentSelectionPayload(selectedSources, options), null, 2),
          }}
          onClose={() => setSaving(false)}
          onSubmit={(data) => {
            onSaveCurrentPreset(data);
            setSaving(false);
          }}
        />
      ) : null}

      {editingPreset ? (
        <PresetFormModal
          title="Edit Preset"
          initial={{
            name: editingPreset.name,
            description: editingPreset.description,
            category: editingPreset.category,
            payloadText: JSON.stringify(editingPreset.payload, null, 2),
          }}
          advanced
          onClose={() => setEditingPreset(null)}
          onSubmit={(data) => {
            onUpdatePreset(editingPreset, data);
            setEditingPreset(null);
          }}
        />
      ) : null}
    </section>
  );
}

function PresetCard({
  preset,
  options,
  running,
  onRun,
  onPreview,
  onApply,
  onDuplicate,
  onEdit,
  onDelete,
}: {
  preset: DiscoveryRunPreset;
  options: DiscoveryOptionsState;
  running: boolean;
  onRun: () => void;
  onPreview: () => void;
  onApply: () => void;
  onDuplicate: () => void;
  onEdit: () => void;
  onDelete: () => void;
}) {
  const needsConfiguration = presetNeedsConfiguration(preset, options);
  return (
    <article className="rounded border border-[#e4e7ec] bg-[#fcfcfd] p-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h3 className="text-base font-semibold text-[#171923]">{preset.name}</h3>
          <p className="mt-1 text-sm text-[#667085]">{preset.description}</p>
        </div>
        <div className="flex shrink-0 flex-wrap gap-2">
          <Badge>{labelizeCategory(preset.category)}</Badge>
          <Badge>{preset.isBuiltIn ? "Built-in" : "Custom"}</Badge>
          {needsConfiguration ? <Badge tone="warning">Requires configuration</Badge> : null}
        </div>
      </div>

      <div className="mt-3 flex flex-wrap gap-2">
        {preset.sources.map((source) => (
          <span key={source} className="rounded border border-[#d9dee8] bg-white px-2 py-1 text-xs font-medium text-[#475467]">
            {sourceLabels[source] ?? source}
          </span>
        ))}
      </div>

      <div className="mt-4 flex flex-wrap gap-2">
        <button type="button" disabled={running} onClick={onRun} className="rounded bg-[#172033] px-3 py-2 text-sm font-medium text-white hover:bg-[#0f1728] disabled:cursor-not-allowed disabled:opacity-60">
          Run
        </button>
        <button type="button" onClick={onPreview} className="rounded border border-[#c8ced8] px-3 py-2 text-sm font-medium text-[#344054] hover:bg-[#f8fafc]">
          Preview Payload
        </button>
        <button type="button" onClick={onApply} className="rounded border border-[#c8ced8] px-3 py-2 text-sm font-medium text-[#344054] hover:bg-[#f8fafc]">
          Apply to Source Selector
        </button>
        <button type="button" onClick={onDuplicate} className="rounded border border-[#c8ced8] px-3 py-2 text-sm font-medium text-[#344054] hover:bg-[#f8fafc]">
          Duplicate
        </button>
        {!preset.isBuiltIn ? (
          <>
            <button type="button" onClick={onEdit} className="rounded border border-[#c8ced8] px-3 py-2 text-sm font-medium text-[#344054] hover:bg-[#f8fafc]">
              Edit
            </button>
            <button type="button" onClick={onDelete} className="rounded border border-[#fecaca] px-3 py-2 text-sm font-medium text-[#991b1b] hover:bg-[#fff7f7]">
              Delete
            </button>
          </>
        ) : null}
      </div>
    </article>
  );
}

export type PresetFormData = {
  name: string;
  description: string;
  category: DiscoveryRunPresetCategory;
  payload: RemoteJobDiscoveryRunRequest;
};

function PresetFormModal({
  title,
  initial,
  advanced = false,
  onClose,
  onSubmit,
}: {
  title: string;
  initial: {
    name: string;
    description: string;
    category: DiscoveryRunPresetCategory;
    payloadText: string;
  };
  advanced?: boolean;
  onClose: () => void;
  onSubmit: (data: PresetFormData) => void;
}) {
  const [name, setName] = useState(initial.name);
  const [description, setDescription] = useState(initial.description);
  const [category, setCategory] = useState<DiscoveryRunPresetCategory>(initial.category);
  const [payloadText, setPayloadText] = useState(initial.payloadText);
  const [error, setError] = useState<string | null>(null);

  function submit() {
    setError(null);
    if (!name.trim()) {
      setError("Preset name is required.");
      return;
    }
    try {
      const payload = JSON.parse(payloadText) as RemoteJobDiscoveryRunRequest;
      if (!Array.isArray(payload.sources) || !payload.sources.length) {
        setError("Preset payload must include at least one source.");
        return;
      }
      onSubmit({
        name: name.trim(),
        description: description.trim(),
        category,
        payload,
      });
    } catch {
      setError("Preset payload JSON is invalid.");
    }
  }

  return (
    <div className="fixed inset-0 z-40 bg-[#101828]/30">
      <div className="absolute right-0 top-0 h-full w-full max-w-2xl overflow-y-auto bg-white p-5 shadow-xl">
        <div className="mb-5 flex items-start justify-between gap-4">
          <div>
            <h2 className="text-lg font-semibold text-[#171923]">{title}</h2>
            <p className="mt-1 text-sm text-[#667085]">Review the payload before saving.</p>
          </div>
          <button type="button" onClick={onClose} className="rounded border border-[#c8ced8] px-3 py-2 text-sm font-medium text-[#344054] hover:bg-[#f8fafc]">
            Close
          </button>
        </div>

        <div className="grid gap-3">
          <Field label="Preset name">
            <input value={name} onChange={(event) => setName(event.target.value)} className="w-full rounded border border-[#c8ced8] px-3 py-2 text-sm" />
          </Field>
          <Field label="Description">
            <textarea value={description} onChange={(event) => setDescription(event.target.value)} className="min-h-20 w-full rounded border border-[#c8ced8] px-3 py-2 text-sm" />
          </Field>
          <Field label="Category">
            <select value={category} onChange={(event) => setCategory(event.target.value as DiscoveryRunPresetCategory)} className="w-full rounded border border-[#c8ced8] px-3 py-2 text-sm">
              {categories.map((item) => (
                <option key={item} value={item}>{labelizeCategory(item)}</option>
              ))}
            </select>
          </Field>
          <Field label={advanced ? "Raw payload JSON" : "Payload preview"}>
            <textarea value={payloadText} onChange={(event) => setPayloadText(event.target.value)} className="min-h-72 w-full rounded border border-[#c8ced8] bg-[#101828] px-3 py-2 font-mono text-xs leading-5 text-white" />
          </Field>
        </div>
        {error ? <p className="mt-3 text-sm text-[#991b1b]">{error}</p> : null}
        <button type="button" onClick={submit} className="mt-4 rounded bg-[#172033] px-3 py-2 text-sm font-medium text-white hover:bg-[#0f1728]">
          Save Preset
        </button>
      </div>
    </div>
  );
}

function PresetPayloadPreview({
  preset,
  payload,
  onClose,
  onRun,
}: {
  preset: DiscoveryRunPreset;
  payload: RemoteJobDiscoveryRunRequest;
  onClose: () => void;
  onRun: () => void;
}) {
  const [copyMessage, setCopyMessage] = useState<string | null>(null);

  async function copy() {
    try {
      await navigator.clipboard.writeText(JSON.stringify(payload, null, 2));
      setCopyMessage("Payload copied.");
    } catch {
      setCopyMessage("Could not copy payload. You can still select the JSON manually.");
    }
  }

  return (
    <div className="fixed inset-0 z-40 bg-[#101828]/30">
      <div className="absolute right-0 top-0 h-full w-full max-w-2xl overflow-y-auto bg-white p-5 shadow-xl">
        <div className="mb-5 flex items-start justify-between gap-4">
          <div>
            <h2 className="text-lg font-semibold text-[#171923]">{preset.name}</h2>
            <p className="mt-1 text-sm text-[#667085]">{preset.sources.map((source) => sourceLabels[source] ?? source).join(", ")}</p>
          </div>
          <button type="button" onClick={onClose} className="rounded border border-[#c8ced8] px-3 py-2 text-sm font-medium text-[#344054] hover:bg-[#f8fafc]">
            Close
          </button>
        </div>
        <div className="flex flex-wrap gap-2">
          <button type="button" onClick={copy} className="rounded border border-[#c8ced8] px-3 py-2 text-sm font-medium text-[#344054] hover:bg-[#f8fafc]">
            Copy Payload
          </button>
          <button type="button" onClick={onRun} className="rounded bg-[#172033] px-3 py-2 text-sm font-medium text-white hover:bg-[#0f1728]">
            Run This Preset
          </button>
        </div>
        {copyMessage ? <p className="mt-3 text-sm text-[#175cd3]">{copyMessage}</p> : null}
        <pre className="mt-4 max-h-[70vh] overflow-auto rounded bg-[#101828] p-4 text-xs leading-5 text-white">
          {JSON.stringify(payload, null, 2)}
        </pre>
      </div>
    </div>
  );
}

function PresetRunsThisSession({ runs }: { runs: PresetRunSessionItem[] }) {
  if (!runs.length) return null;
  return (
    <div className="mt-5 rounded border border-[#e4e7ec] bg-[#fcfcfd] p-4">
      <h3 className="text-sm font-semibold text-[#344054]">Preset Runs This Session</h3>
      <div className="mt-3 overflow-x-auto">
        <table className="min-w-full text-left text-sm">
          <thead className="border-b border-[#e4e7ec] text-xs uppercase tracking-normal text-[#667085]">
            <tr>
              <th className="py-2 pr-4 font-semibold">Preset</th>
              <th className="py-2 pr-4 font-semibold">Started</th>
              <th className="py-2 pr-4 font-semibold">Status</th>
              <th className="py-2 pr-4 font-semibold">Sources</th>
              <th className="py-2 pr-4 font-semibold">Jobs Scored</th>
              <th className="py-2 pr-4 font-semibold">Warnings</th>
            </tr>
          </thead>
          <tbody>
            {runs.map((run) => (
              <tr key={`${run.presetId}-${run.startedAt}`} className="border-b border-[#eef2f6] last:border-0">
                <td className="py-2 pr-4 font-medium text-[#171923]">{run.presetName}</td>
                <td className="py-2 pr-4 text-[#475467]">{new Date(run.startedAt).toLocaleString()}</td>
                <td className="py-2 pr-4 text-[#475467]">{run.status}</td>
                <td className="py-2 pr-4 text-[#475467]">{run.sources.join(", ")}</td>
                <td className="py-2 pr-4 text-[#475467]">{run.jobsScored}</td>
                <td className="py-2 pr-4 text-[#475467]">{run.warningsCount}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function currentSelectionPayload(
  selectedSources: string[],
  options: DiscoveryOptionsState,
): RemoteJobDiscoveryRunRequest {
  const payload: RemoteJobDiscoveryRunRequest = {
    force: true,
    score_after_ingestion: true,
    sources: selectedSources,
  };
  if (selectedSources.includes("himalayas")) payload.himalayas = options.himalayas;
  if (selectedSources.includes("we_work_remotely")) payload.we_work_remotely = options.we_work_remotely;
  if (selectedSources.includes("remotive")) payload.remotive = options.remotive;
  if (selectedSources.includes("hacker_news")) payload.hacker_news = options.hacker_news;
  if (selectedSources.includes("ycombinator")) payload.ycombinator = options.ycombinator;
  if (selectedSources.includes("ashby")) {
    payload.ashby = {
      ...options.ashby,
      board_slugs: (options.ashby.board_slugs_text ?? "").split(",").map((item) => item.trim()).filter(Boolean),
    };
  }
  return payload;
}

function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <label className="block text-sm font-medium text-[#344054]">
      <span className="mb-1 block">{label}</span>
      {children}
    </label>
  );
}

function Badge({ children, tone = "default" }: { children: ReactNode; tone?: "default" | "warning" }) {
  const classes = tone === "warning"
    ? "border-[#fedf89] bg-[#fffbeb] text-[#92400e]"
    : "border-[#d9dee8] bg-white text-[#475467]";
  return <span className={`rounded border px-2.5 py-1 text-xs font-semibold ${classes}`}>{children}</span>;
}

function labelizeCategory(category: string) {
  return category.replace(/_/g, " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function recommendedPresetName(advisors: SourceQualityAdvisorItem[], presets: DiscoveryRunPreset[]) {
  const daily = advisors.filter((advisor) => ["run_daily", "run_every_few_days"].includes(advisor.recommendation));
  if (daily.length) return "Custom Daily Scout based on advisor";
  if (!advisors.some((advisor) => advisor.totalRuns > 0)) return "Remote Jobs Only";
  const hn = advisors.find((advisor) => advisor.source === "hacker_news");
  if (hn && (hn.qualityScore >= 45 || (hn.noiseScore ?? 0) < 50)) return "HN Startup Signals";
  const ashby = advisors.find((advisor) => advisor.source === "ashby");
  if (ashby?.recommendation === "needs_configuration") return "Ashby Board Debug";
  return presets[0]?.name ?? null;
}
