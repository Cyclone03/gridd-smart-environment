import { KeyRound } from "lucide-react";
import { useState } from "react";
import { Navigate, useNavigate, useSearchParams } from "react-router";
import { PageHeader } from "../components/common/PageHeader";
import { LoginForm } from "../components/forms/LoginForm";
import { errorMessage } from "../requests/httpClient";
import type { Credentials } from "../resources/auth";
import { useAuth } from "../stores/authStore";

/** N'accepte que des chemins internes pour la redirection après connexion. */
function safeNext(value: string | null): string {
  return value && value.startsWith("/") && !value.startsWith("//") ? value : "/";
}

export function LoginView() {
  const { user, login } = useAuth();
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const next = safeNext(params.get("next"));
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (user) return <Navigate to={next} replace />;

  const submit = async (credentials: Credentials) => {
    setSubmitting(true);
    setError(null);
    try {
      await login(credentials);
      navigate(next, { replace: true });
    } catch (reason) {
      setError(errorMessage(reason, "Connexion impossible."));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <main className="dashboard page-view narrow">
      <PageHeader
        icon={KeyRound}
        overline="Connexion"
        title="Accès gestionnaire"
        description="La consultation est libre. Une connexion est nécessaire pour gérer les règles d’alarme."
      />
      <section className="login-card">
        <LoginForm submitting={submitting} serverError={error} onSubmit={submit} />
        <p className="muted-note">Les comptes sont créés par un administrateur dans l’administration Django.</p>
      </section>
    </main>
  );
}
