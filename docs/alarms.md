# Règles d'alarme

Les utilisateurs autorisés définissent les conditions de déclenchement des
alarmes depuis l'interface (**Règles d'alarme**, `/alarms/rules`), sans
modifier le code. Les règles sont enregistrées par l'API et **évaluées par le
serveur à chaque nouvelle mesure**, que l'interface soit ouverte ou non.

## Droits

| Action | Qui |
|---|---|
| Consulter les règles et les alertes | tout le monde, sans compte |
| Créer | permission `core.add_alarmrule` |
| Modifier, activer, désactiver | permission `core.change_alarmrule` |
| Supprimer | permission `core.delete_alarmrule` |

Le groupe **« Gestionnaires des alarmes »** (créé automatiquement par
`migrate`) possède ces quatre permissions. L'interface masque les actions non
autorisées ; l'API les refuse de toute façon (401/403).

## Composition d'une règle

| Champ | Description |
|---|---|
| Nom, description | Identification (le nom apparaît dans les alertes) |
| Paramètre surveillé | Température (°C), humidité (%), niveau sonore (dBA), occupation (personnes), CO₂ (ppm) |
| Espace | Un espace précis, ou **tous les espaces** |
| Condition | `>`, `≥`, `<`, `≤`, en dehors d'un intervalle, à l'intérieur d'un intervalle |
| Seuil(s) | Une valeur, ou borne basse + borne haute pour un intervalle. L'unité est imposée par le paramètre. |
| Gravité | Information, avertissement, critique |
| Durée minimale | Temps pendant lequel la condition doit rester vraie avant de déclencher (0 = immédiat) |
| Hystérésis | Marge à franchir dans l'autre sens pour revenir à la normale |
| Active | Une règle inactive n'est jamais évaluée |

Le formulaire affiche en direct une phrase **« Comportement attendu »**, par
exemple : *Une alarme « avertissement » sera déclenchée lorsque la mesure
« Température » sera > 28 °C dans « Salle de réunion » pendant au moins
5 min. Elle sera résolue lorsque la valeur reviendra d'au moins 0,5 °C dans la
zone normale.*

### Validation

Contrôlée dans le formulaire puis par l'API :

- nom obligatoire, paramètre et condition valides ;
- intervalle : borne haute obligatoire et supérieure à la borne basse ;
- seuils compris dans les limites physiques du capteur (température −20 à
  60 °C, humidité 0 à 100 %, son 0 à 150 dBA, occupation 0 à 500) ;
- occupation : seuils et hystérésis entiers (c'est un comptage) ;
- hystérésis positive, et inférieure à la moitié de l'intervalle pour
  « en dehors de l'intervalle » ;
- durée minimale entre 0 et 24 h.

Les nombres acceptent la virgule décimale (`21,5`).

### Exemples (valeurs illustratives)

| Besoin | Règle |
|---|---|
| Température trop élevée | Température `>` 28 °C, durée 10 min, hystérésis 0,5 °C |
| Humidité hors confort | Humidité *en dehors de* [30 ; 60] %, hystérésis 2 % |
| Capacité dépassée | Occupation `>` 30 personnes, gravité critique |
| Bruit prolongé | Niveau sonore `>` 70 dBA pendant 5 min, hystérésis 3 dBA |

Ces valeurs **ne sont pas des normes** : elles dépendent de l'usage de
l'espace, des équipements et des exigences applicables.

## Évaluation

Chaque observation reçue (Kafka ou simulateur) passe par
`core.services.ingest_observation`, qui appelle
`core.alarm_engine.evaluate_alarm_rules` dans la même transaction. Pour chaque
règle active portant sur ce paramètre et sur cet espace (ou sur tous les
espaces), un état est tenu par couple (règle, espace) :

```text
NORMAL ──condition vraie──► EN ATTENTE ──durée minimale atteinte──► EN ALARME
   ▲   (durée 0 : directement EN ALARME)                                  │
   ├───────── condition redevenue fausse pendant l'attente               │
   └──────────── retour à la normale, hystérésis comprise ◄──────────────┘
```

- **Déclenchement** : création d'une alerte (`Alert`) avec la règle, l'espace,
  la valeur déclenchante (`trigger_value`), la gravité et un message explicite.
- **Situation persistante** : pas de nouvelle alerte ; l'alerte existante est
  rattachée à la dernière mesure. Il n'y a jamais deux alertes actives pour la
  même règle et le même espace.
- **Retour à la normale** : l'alerte est close (`resolved_at`,
  `resolution: "returned_to_normal"`). Un nouveau dépassement ultérieur crée
  un nouvel épisode.
- **Hystérésis** : pour `> 30` avec 1 d'hystérésis, l'alarme se déclenche
  au-dessus de 30 et ne se résout qu'à 29 ou moins ; pour « en dehors de
  [30 ; 60] » avec 1, elle se résout entre 31 et 59. Cela évite les
  oscillations autour d'un seuil.
- **Durée minimale** : mesurée sur les horodatages des observations. Un pic
  isolé plus court que la durée ne déclenche rien. La durée n'est vérifiée
  qu'à l'arrivée d'une mesure : la précision dépend donc de la fréquence des
  capteurs (environ une minute).
- **Mesures invalides** (hors limites physiques) : ignorées par les règles ;
  elles produisent déjà une alerte de qualité des données.
- **Mesures en retard** (plus anciennes que la dernière évaluée) : ignorées,
  pour qu'un message Kafka rejoué ne modifie pas l'état courant.

Les tableaux de bord sont notifiés en temps réel (`alerts.changed` sur le
WebSocket) à chaque création ou résolution.

### Modifier une règle

| Modification | Effet |
|---|---|
| Désactivation | alertes en cours closes (« Règle désactivée ») |
| Condition (paramètre, espace, opérateur, seuils, durée, hystérésis) | alertes en cours closes (« Règle modifiée ») ; la règle est réévaluée dès la mesure suivante |
| Gravité | appliquée aux alertes en cours |
| Nom, description | aucun effet sur les alertes |
| Suppression | alertes en cours closes (« Règle supprimée ») ; l'historique est conservé |

Les modifications faites dans l'admin Django ne déclenchent pas ces effets :
préférer l'interface ou l'API.

## Consultation des alarmes

Page **Alertes** (`/alerts`) :

- alertes actives (règles et qualité des données), marquables comme
  consultées (préférence conservée dans le navigateur) ;
- règles qui s'appliquent à l'espace choisi ;
- historique des déclenchements résolus des 7 derniers jours (heure de
  déclenchement et de résolution, espace, origine, gravité, motif).

Toute la traçabilité est disponible par l'API : `GET /api/alerts/?rule=<id>`,
`?since=…&until=…` (voir [`api.md`](api.md#alertes-et-événements)).

## Qualité des données

Indépendamment des règles, le serveur marque chaque mesure :

- **invalide** : hors limites physiques → alerte critique `DATA_QUALITY_<TYPE>` ;
- **suspecte** : variation plus rapide que le maximum du profil de la zone, ou
  valeur inchangée depuis `stuck_after_minutes` → alerte d'avertissement.

Ces réglages restent dans le profil de chaque zone (admin Django → Zones).
L'alerte se résout dès qu'une mesure redevient normale.

## Migration des anciens seuils

Avant la refonte, les seuils étaient des colonnes fixes de `ThresholdProfile`
(température min/max, humidité min/max, son avertissement/critique). La
migration `0012_convert_thresholds_to_rules` les convertit :

| Ancien seuil | Règle créée |
|---|---|
| `temperature_min` / `temperature_max` | « Température hors plage » : en dehors de [min ; max], avertissement |
| `humidity_min` / `humidity_max` | « Humidité hors plage » : en dehors de [min ; max], avertissement |
| `sound_warning` | « Niveau sonore élevé » : ≥ seuil, avertissement |
| `sound_critical` | « Niveau sonore critique » : > seuil, critique |

- Les règles sont actives si le profil l'était.
- Si tous les profils ont les mêmes valeurs, quatre règles **globales** sont
  créées ; sinon, quatre règles par espace.
- Les seuils CO₂, jamais évalués auparavant, ne sont pas convertis.
- Les anciennes alertes de seuil encore actives sont closes
  (`resolution: "migrated"`).
- Différence de comportement : au-delà du seuil critique sonore, l'ancien code
  ne gardait que l'alerte critique ; désormais, les deux règles sonores sont
  actives simultanément (avertissement + critique). Désactiver ou ajuster
  « Niveau sonore élevé » si ce n'est pas souhaité.

Sur la base fournie avec le projet, les sept profils étaient identiques et
désactivés : la migration produit donc quatre règles globales inactives, à
activer et ajuster depuis l'interface.

La migration `0013` supprime ensuite ces colonnes. Un retour arrière
(`migrate core 0011`) recrée les colonnes avec leurs valeurs par défaut, sans
restaurer les valeurs personnalisées.

## Données de démonstration

`python manage.py seed_gridd` crée, si aucune règle n'existe, quatre règles
illustratives : température hors de [18 ; 28] °C, humidité hors de
[30 ; 60] %, son > 70 dBA pendant 1 min, occupation > 30 personnes.
