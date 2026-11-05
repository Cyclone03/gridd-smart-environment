import type { LucideIcon } from "lucide-react";
import type { ReactNode } from "react";

export function PageHeader({
  icon: Icon,
  overline,
  title,
  description,
  aside,
}: {
  icon: LucideIcon;
  overline: string;
  title: string;
  description?: ReactNode;
  aside?: ReactNode;
}) {
  return (
    <header className="page-head">
      <div>
        <span className="overline">
          <Icon size={15} aria-hidden="true" /> {overline}
        </span>
        <h1>{title}</h1>
        {description && <p>{description}</p>}
      </div>
      {aside}
    </header>
  );
}
