import { RotateCcw, Save } from "lucide-react";
import { useId, useState, type FormEvent } from "react";
import {
  draftFromProfile,
  validateProfileDraft,
  type ProfileDraft,
  type ProfileErrors,
  type ProfileFieldMeta,
} from "../../resources/profile";
import { ErrorMessage } from "../common/Feedback";

/**
 * Formulaire de paramètres numériques d'un espace (plages de confort, modèle
 * énergétique). Validation immédiate, puis erreurs renvoyées par l'API.
 */
export function ProfileForm<K extends string>({
  label,
  fields,
  profile,
  customized,
  submitting,
  serverMessage,
  serverErrors = {},
  cross,
  onSubmit,
  onReset,
}: {
  label: string;
  fields: ProfileFieldMeta<K>[];
  profile: Record<K, number>;
  customized: boolean;
  submitting: boolean;
  serverMessage?: string | null;
  serverErrors?: Record<string, string>;
  cross?: (values: Record<K, number>) => ProfileErrors<K>;
  onSubmit: (values: Record<K, number>) => void;
  onReset: () => void;
}) {
  const id = useId();
  const [draft, setDraft] = useState<ProfileDraft<K>>(() => draftFromProfile(profile));
  const [errors, setErrors] = useState<ProfileErrors<K>>({});
  const groups = Array.from(new Set(fields.map((field) => field.group)));

  const submit = (event: FormEvent) => {
    event.preventDefault();
    const result = validateProfileDraft(fields, draft, cross);
    setErrors(result.errors);
    if (result.values) onSubmit(result.values);
  };

  return (
    <form className="profile-form" onSubmit={submit} noValidate aria-label={label}>
      {serverMessage && <ErrorMessage>{serverMessage}</ErrorMessage>}
      {groups.map((group) => (
        <fieldset key={group}>
          <legend>{group}</legend>
          <div className="form-grid">
            {fields
              .filter((field) => field.group === group)
              .map((field) => {
                const error = errors[field.key] ?? serverErrors[field.key];
                const inputId = `${id}-${field.key}`;
                return (
                  <div className="field" key={field.key}>
                    <label htmlFor={inputId}>{field.label}</label>
                    <div className="input-suffix">
                      <input
                        id={inputId}
                        inputMode="decimal"
                        value={draft[field.key]}
                        aria-invalid={Boolean(error)}
                        aria-describedby={error ? `${inputId}-error` : undefined}
                        onChange={(event) => setDraft((current) => ({ ...current, [field.key]: event.target.value }))}
                      />
                      {field.unit && <i>{field.unit}</i>}
                    </div>
                    {field.hint && <small>{field.hint}</small>}
                    {error && (
                      <em className="field-error" id={`${inputId}-error`}>
                        {error}
                      </em>
                    )}
                  </div>
                );
              })}
          </div>
        </fieldset>
      ))}
      <div className="form-actions">
        <span className={`badge ${customized ? "badge-on" : "badge-off"}`}>
          {customized ? "Valeurs personnalisées" : "Valeurs par défaut du type d’espace"}
        </span>
        {customized && (
          <button type="button" className="secondary-button" onClick={onReset} disabled={submitting}>
            <RotateCcw size={15} aria-hidden="true" /> Valeurs par défaut
          </button>
        )}
        <button type="submit" className="primary-button" disabled={submitting}>
          <Save size={15} aria-hidden="true" /> {submitting ? "Enregistrement…" : "Enregistrer"}
        </button>
      </div>
    </form>
  );
}
