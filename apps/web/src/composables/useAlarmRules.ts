import { useCallback, useState } from "react";
import { errorMessage } from "../requests/httpClient";
import type { AlarmMetadata, AlarmRule } from "../resources/alarmRule";
import { deleteAlarmRule, getAlarmMetadata, listAlarmRules, setAlarmRuleEnabled } from "../services/alarmRulesService";
import { useAsyncData } from "./useAsyncData";

/**
 * Liste des règles d'alarme et actions rapides (activer, désactiver,
 * supprimer). Les erreurs d'action sont exposées séparément de l'erreur de
 * chargement pour ne pas masquer la liste.
 */
export function useAlarmRules(filters: { zone?: string } = {}) {
  const rules = useAsyncData<AlarmRule[]>((signal) => listAlarmRules(filters, signal), [filters.zone], {
    keepPrevious: true,
  });
  const metadata = useAsyncData<AlarmMetadata>(() => getAlarmMetadata(), []);
  const [actionError, setActionError] = useState<string | null>(null);
  const [pendingId, setPendingId] = useState<number | null>(null);

  const run = useCallback(
    async (id: number, action: () => Promise<unknown>) => {
      setPendingId(id);
      setActionError(null);
      try {
        await action();
        rules.reload();
      } catch (error) {
        setActionError(errorMessage(error));
      } finally {
        setPendingId(null);
      }
    },
    [rules],
  );

  return {
    rules: rules.data ?? [],
    metadata: metadata.data,
    loading: rules.loading || metadata.loading,
    error: rules.error ?? metadata.error,
    reload: rules.reload,
    actionError,
    pendingId,
    toggle: (rule: AlarmRule) => run(rule.id, () => setAlarmRuleEnabled(rule.id, !rule.enabled)),
    remove: (rule: AlarmRule) => run(rule.id, () => deleteAlarmRule(rule.id)),
  };
}
