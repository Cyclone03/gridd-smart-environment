import { AlertTriangle, CheckCircle2, LoaderCircle } from "lucide-react";
import type { ReactNode } from "react";

/** Message d'erreur annoncé aux technologies d'assistance. */
export function ErrorMessage({ children, onRetry }: { children: ReactNode; onRetry?: () => void }) {
  return (
    <div className="error-banner" role="alert">
      <AlertTriangle size={17} aria-hidden="true" />
      <span>{children}</span>
      {onRetry && (
        <button type="button" onClick={onRetry}>
          Réessayer
        </button>
      )}
    </div>
  );
}

export function Loading({ label = "Chargement…" }: { label?: string }) {
  return (
    <div className="loading-state" role="status">
      <LoaderCircle size={18} className="spin" aria-hidden="true" />
      {label}
    </div>
  );
}

export function EmptyState({ title, children }: { title: string; children?: ReactNode }) {
  return (
    <div className="empty-state">
      <CheckCircle2 size={28} aria-hidden="true" />
      <strong>{title}</strong>
      {children && <span>{children}</span>}
    </div>
  );
}
