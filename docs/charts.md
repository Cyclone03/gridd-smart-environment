# Graphiques et périodes d'observation

L'écran **Analyse historique** (`/history`) affiche, pour un espace et une
mesure, la courbe des moyennes par créneau, des statistiques et l'analyse des
corrélations entre température, humidité et niveau sonore. Tous ces éléments
utilisent la **même période d'observation**, choisie par l'utilisateur.

## Utilisation

1. Choisir un espace dans la colonne de gauche. Seules les mesures dont
   l'espace possède un capteur actif sont proposées.
2. Choisir la mesure (onglets). Une pastille verte indique qu'une valeur a
   déjà été reçue.
3. Dans le bloc **Période**, sélectionner :
   - une période prédéfinie : 15 dernières minutes, dernière heure,
     6 dernières heures, 24 dernières heures, aujourd'hui, hier,
     7 derniers jours, 30 derniers jours ;
   - ou **Période personnalisée…**, puis la date et l'heure de début et de fin.
4. Cliquer sur **Appliquer**. Tant que ce n'est pas fait, la mention
   « Modification non appliquée » rappelle que le graphique montre encore
   l'ancienne période.

La ligne **Période affichée** indique en permanence la période réellement
représentée et ses bornes. L'en-tête du graphique précise la granularité
(« Moyennes par créneau de 5 min »), choisie par l'API selon la durée.

Le bouton ⟳ actualise les données. Les périodes glissantes (« dernière
heure »…) sont en plus recalculées automatiquement chaque minute ; les
périodes fixes (« hier », plage personnalisée) ne changent pas.

La période fait partie de l'URL (`?period=24h` ou `?start=…&end=…`, avec
`zone` et `metric`) : l'adresse peut être partagée ou mise en favori, et un
rechargement de page conserve la sélection. Les anciens liens `?date=AAAA-MM-JJ`
restent compris.

## Comportement

| Situation | Affichage |
|---|---|
| Chargement initial | « Chargement des mesures… » |
| Actualisation | l'ancienne courbe reste visible, mention « actualisation… » |
| Aucune mesure | « Aucune mesure enregistrée pour cette période. » |
| Erreur de l'API (ex. période trop longue) | message de l'API et bouton **Réessayer** |
| Plage invalide | message sous le champ concerné, rien n'est envoyé |

Validation côté interface : dates présentes, début non futur, fin postérieure
au début, durée ≤ 31 jours. L'API applique les mêmes contrôles (et reste
l'autorité, voir `HISTORY_MAX_RANGE_DAYS`).

## Fonctionnement technique

```text
PeriodSelector ─ onApply ─► useObservationPeriod (URL ?period / ?start&end)
                                  │ resolvePeriod() → { start, end, label, live }
                                  ▼
             useZoneHistory / useCorrelationSeries ─► historyService.getZoneHistory
                                  │                         │
                                  │   GET /api/zones/<code>/history/?type&start&end
                                  ▼
                  HistoryChart · HistoryStats · CorrelationPanel
```

- Les bornes sont envoyées en UTC (ISO 8601). Le serveur filtre les
  observations en base (index `zone, type, observed_at`), choisit la
  granularité et **agrège côté serveur** : le navigateur reçoit au plus
  quelques centaines de créneaux, jamais les mesures brutes. La durée maximale
  (31 jours) borne le volume lu : mesuré sur PostgreSQL, 30 jours d'une
  mesure par minute (44 640 lignes) répondent en ~0,4 s, 24 h en ~0,06 s. Au-delà, une agrégation SQL ou des tables de
  synthèse seraient à envisager.
- Pour 30 jours, la granularité automatique est de 3 h (240 créneaux) ;
  pour 7 jours, 30 min ; pour 24 h, 5 min ; pour 1 h, 1 min.
- Un changement de période annule la requête précédente (`AbortController`)
  et ne déclenche qu'un seul chargement.
- `useAsyncData` conserve la dernière courbe pendant une actualisation.

### Ajuster les périodes proposées

Les préréglages sont dans `web/src/constants/periods.ts` (`PERIOD_PRESETS`).
La limite de durée côté interface (`MAX_RANGE_DAYS`) doit rester alignée sur
`HISTORY_MAX_RANGE_DAYS` de l'API. Les granularités possibles sont dans
`apps/api/core/history.py` (`BUCKET_CHOICES_MINUTES`).

Les capteurs envoient environ une mesure par minute : en deçà de 15 minutes, la
courbe compte trop peu de points pour être utile, d'où l'absence de période
plus courte.

## Corrélations

Le panneau calcule, sur la période appliquée, le coefficient de Pearson entre
chaque paire de mesures disponibles (au moins 8 créneaux communs), la valeur p
(indicative), un éventuel effet retardé et la corrélation partielle pour
repérer les liens indirects. Une corrélation n'implique pas de causalité.
Code : `web/src/utils/correlation.ts` (calculs) et
`web/src/utils/correlationInsights.ts` (interprétation).

## Autres indicateurs

La **vue d'ensemble** affiche des moyennes sur les dernières mesures et des
indices de confort indicatifs. Leurs repères (température et humidité de
référence, capacité de 30 personnes…) sont regroupés dans
`web/src/constants/comfort.ts` : ce ne sont pas des normes.

L'indicateur « Prochaine valeur (indicative) » reprend l'heuristique existante
(dernière moyenne ± un pas fixe selon la tendance, `utils/prediction.ts`) ;
ce n'est pas un modèle de prévision.
