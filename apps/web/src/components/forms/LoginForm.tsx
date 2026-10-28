import { LogIn } from "lucide-react";
import { useId, useState, type FormEvent } from "react";
import { validateCredentials, type Credentials } from "../../resources/auth";
import type { FieldErrors } from "../../types/common";
import { ErrorMessage } from "../common/Feedback";

export function LoginForm({
  submitting,
  serverError,
  onSubmit,
}: {
  submitting: boolean;
  serverError: string | null;
  onSubmit: (credentials: Credentials) => void;
}) {
  const id = useId();
  const [values, setValues] = useState<Credentials>({ username: "", password: "" });
  const [errors, setErrors] = useState<FieldErrors<keyof Credentials>>({});

  const submit = (event: FormEvent) => {
    event.preventDefault();
    const validation = validateCredentials(values);
    setErrors(validation);
    if (!Object.keys(validation).length) onSubmit({ ...values, username: values.username.trim() });
  };

  return (
    <form className="login-form" onSubmit={submit} noValidate>
      {serverError && <ErrorMessage>{serverError}</ErrorMessage>}
      <div className="field">
        <label htmlFor={`${id}-username`}>Identifiant</label>
        <input
          id={`${id}-username`}
          autoComplete="username"
          value={values.username}
          onChange={(event) => setValues((current) => ({ ...current, username: event.target.value }))}
          aria-invalid={Boolean(errors.username)}
        />
        {errors.username && <em className="field-error">{errors.username}</em>}
      </div>
      <div className="field">
        <label htmlFor={`${id}-password`}>Mot de passe</label>
        <input
          id={`${id}-password`}
          type="password"
          autoComplete="current-password"
          value={values.password}
          onChange={(event) => setValues((current) => ({ ...current, password: event.target.value }))}
          aria-invalid={Boolean(errors.password)}
        />
        {errors.password && <em className="field-error">{errors.password}</em>}
      </div>
      <button type="submit" className="primary-button" disabled={submitting}>
        <LogIn size={15} aria-hidden="true" /> {submitting ? "Connexion…" : "Se connecter"}
      </button>
    </form>
  );
}
