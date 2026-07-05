import { PageHeader } from "@/components/layout/PageHeader";

export function PlaceholderPage({
  title,
  description,
}: {
  title: string;
  description: string;
}) {
  return (
    <>
      <PageHeader title={title} description={description} />
      <div className="rounded-md border border-dashed border-[#c8ced8] bg-white p-8">
        <p className="text-sm text-[#667085]">
          This section is reserved for a later ScoutAI brick.
        </p>
      </div>
    </>
  );
}
