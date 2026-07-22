import type { ReactNode } from "react";

type PageHeaderProps = {
  title: string;
  description?: string;
  subtitle?: string;
  eyebrow?: string;
  breadcrumbs?: Array<{ label: string; href?: string }>;
  actions?: ReactNode;
};

export function PageHeader({ title, description, subtitle, eyebrow, breadcrumbs, actions }: PageHeaderProps) {
  const supportingText = subtitle ?? description;
  return (
    <div className="mb-6 flex flex-col gap-4 border-b border-[#d9dee8] pb-5 sm:flex-row sm:items-end sm:justify-between">
      <div>
        {breadcrumbs?.length ? (
          <div className="mb-2 flex flex-wrap gap-1 text-xs text-[#667085]">
            {breadcrumbs.map((item, index) => (
              <span key={`${item.label}-${index}`}>
                {item.href ? <a href={item.href} className="font-medium text-[#175cd3]">{item.label}</a> : item.label}
                {index < breadcrumbs.length - 1 ? <span className="mx-1 text-[#98a2b3]">/</span> : null}
              </span>
            ))}
          </div>
        ) : null}
        {eyebrow ? <p className="mb-1 text-xs font-semibold uppercase tracking-normal text-[#667085]">{eyebrow}</p> : null}
        <h1 className="text-2xl font-semibold tracking-normal text-[#171923]">
          {title}
        </h1>
        {supportingText ? (
          <p className="mt-1 max-w-2xl text-sm leading-6 text-[#667085]">
            {supportingText}
          </p>
        ) : null}
      </div>
      {actions ? <div className="flex flex-wrap items-center gap-2 sm:justify-end">{actions}</div> : null}
    </div>
  );
}
