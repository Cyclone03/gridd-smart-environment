import { ArrowLeft, BellRing } from "lucide-react";
import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router";
import { ErrorMessage, Loading } from "../components/common/Feedback";
import { PageHeader } from "../components/common/PageHeader";
import { AlarmRuleForm } from "../components/forms/AlarmRuleForm";
import { useAsyncData } from "../composables/useAsyncData";
import { ApiError, errorMessage } from "../requests/httpClient";
import { draftFromRule, emptyAlarmRuleDraft, type AlarmRulePayload } from "../resources/alarmRule";
import { routePath } from "../routes/definitions";
import { createAlarmRule, getAlarmMetadata, getAlarmRule, updateAlarmRule } from "../services/alarmRulesService";
import { useDashboard } from "../stores/dashboardStore";

/** Création (`/alarms/rules/new`) ou modification (`/alarms/rules/:ruleId/edit`) d'une règle. */
export function AlarmRuleEditView() {
  const { ruleId } = useParams();
  const id = ruleId ? Number(ruleId) : null;
  const navigate = useNavigate();
  const { zones } = useDashboard();
  const metadata = useAsyncData(() => getAlarmMetadata(), []);
  const rule = useAsyncData(id ? (signal) => getAlarmRule(id, signal) : null, [id]);
  const [submitting, setSubmitting] = useState(false);
  const [serverError, setServerError] = useState<{ message: string; fields: Record<string, string> } | null>(null);

  const editing = id !== null;
  const backTo = routePath("alarmRules");

  const submit = async (payload: AlarmRulePayload) => {
    setSubmitting(true);
    setServerError(null);
    try {
      if (editing) await updateAlarmRule(id, payload);
      else await createAlarmRule(payload);
      navigate(backTo);
    } catch (error) {
      setServerError({
        message: errorMessage(error, "Enregistrement impossible."),
        fields: error instanceof ApiError ? error.fieldErrors : {},
      });
    } finally {
      setSubmitting(false);
    }
  };

  const loadError = metadata.error ?? rule.error;
  const ready = metadata.data && (!editing || rule.data);

  return (
    <main className="dashboard page-view narrow">
      <Link className="back-link" to={backTo}>
        <ArrowLeft size={15} aria-hidden="true" /> Retour aux règles
      </Link>
      <PageHeader
        icon={BellRing}
        overline="Règles d’alarme"
        title={editing ? "Modifier la règle" : "Nouvelle règle d’alarme"}
        description="Les seuils proposés ne sont pas des normes : adaptez-les à l’usage de l’espace et aux capteurs disponibles."
      />
      {loadError && (
        <ErrorMessage
          onRetry={() => {
            metadata.reload();
            rule.reload();
          }}
        >
          {loadError}
        </ErrorMessage>
      )}
      {!loadError && !ready && <Loading />}
      {ready && (
        <AlarmRuleForm
          key={rule.data?.id ?? "new"}
          initial={rule.data ? draftFromRule(rule.data) : emptyAlarmRuleDraft()}
          metadata={metadata.data!}
          zones={zones}
          submitting={submitting}
          serverMessage={serverError?.message}
          serverErrors={serverError?.fields}
          submitLabel={editing ? "Enregistrer les modifications" : "Créer la règle"}
          onSubmit={submit}
          onCancel={() => navigate(backTo)}
        />
      )}
    </main>
  );
}
