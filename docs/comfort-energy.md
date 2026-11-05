# Confort thermique et consommation énergétique

Deux services s'ajoutent aux alarmes. Ils s'appuient sur les mêmes mesures
(Kafka → ingestion → database) et publient leurs résultats sur leurs propres
topics, enregistrés par le module Database.

| Service | Module | Déclenché par | Résultat enregistré |
|---|---|---|---|
| Confort thermique | `modules/comfort` | chaque mesure de température ou d'humidité | une évaluation (`ComfortAssessment`) |
| Énergie | `modules/energy` | chaque mesure de température ou d'occupation | un intervalle estimé (`EnergyEstimate`) |

Les paramètres de chaque espace ont des **valeurs par défaut selon le type
d'espace**. On les personnalise depuis l'interface (pages *Confort* et
*Énergie*) ou par l'API (`PATCH`). `DELETE` rétablit les valeurs par défaut.
Une modification s'applique aux mesures suivantes ; l'historique n'est pas
recalculé.

## Confort thermique

### Méthode : plages de température et d'humidité

Pour chaque facteur (température, humidité relative) :

| Position de la mesure | État | Score du facteur |
|---|---|---|
| dans `[min ; max]` | `ok` | 100 |
| hors plage, écart ≤ tolérance | léger écart : `cool`/`warm`, `dry`/`humid` | 100 → 50 |
| écart > tolérance | écart marqué : `too_cold`/`too_hot`, `too_dry`/`too_humid` | 50 → 0 (0 à 2 × tolérance) |

- **Niveau** : `uncomfortable` si un facteur est en écart marqué,
  `acceptable` s'il y a un léger écart, `comfortable` sinon, `unknown` sans
  aucune mesure.
- **Score global** (0–100) : moyenne pondérée des facteurs disponibles,
  température 70 %, humidité 30 %.
- À chaque mesure, l'autre facteur est la dernière mesure valide de la zone de
  moins de `COMFORT_MAX_INPUT_AGE_MINUTES` (30 min). Sans elle, l'évaluation
  repose sur un seul facteur. Les mesures invalides sont ignorées.

### Plages par défaut

| Type d'espace | Température | Tolérance | Humidité | Tolérance |
|---|---|---|---|---|
| Bureaux, salles de réunion et de cours, cubicules, espaces ouverts, laboratoires, autres | 20–24 °C | 2 °C | 30–60 % | 10 % |
| Salle serveur | 18–27 °C | 5 °C | 20–60 % | 20 % |

Ordres de grandeur usuels en saison de chauffage (proches des recommandations
ASHRAE 55 / ISO 7730 pour les espaces occupés, ASHRAE TC 9.9 pour les
équipements) : ce ne sont pas des exigences réglementaires.

## Consommation énergétique

> Les capteurs GRIDD ne mesurent pas l'énergie. Les valeurs affichées sont des
> **estimations** produites par un modèle paramétrable : leur fiabilité dépend
> des paramètres saisis pour chaque espace.

### Modèle

Puissance électrique d'un espace, en W :

```text
éclairage    = surface × densité d'éclairage          (× 10 % sans occupant)
équipements  = puissance fixe + puissance par personne × occupants
pertes       = (UA + 1,2 × air neuf par personne × occupants) × (T_int − T_ext)
apports      = 75 W × occupants + éclairage + équipements
besoin       = pertes − apports
chauffage    = besoin ÷ COP chauffage      si besoin > 0
climatisation = −besoin ÷ COP froid        si besoin < 0
```

- `T_int` : dernière température mesurée de la zone ; `T_ext` : température
  extérieure de référence du profil. Sans température intérieure, le
  chauffage et la climatisation ne sont pas estimés (`hvac_estimated = false`).
- Occupants : dernière mesure d'occupation de la zone, sinon l'occupation par
  défaut du profil (`occupancy_source` : `sensor` ou `profile`).
- 1,2 W par (L/s) et par degré : chaleur volumique de l'air (ρ·c ≈ 1,2 kJ/(m³·K)).

### Intégration dans le temps

Chaque mesure valide de température ou d'occupation clôt l'intervalle ouvert
par la mesure précédente de la zone. L'énergie de l'intervalle vaut la
puissance calculée avec les valeurs connues à son début, multipliée par sa
durée.

Ne sont pas estimés :

- la première mesure d'une zone ;
- un intervalle de plus de `ENERGY_MAX_INTERVAL_MINUTES` (15 min, capteur muet) ;
- une mesure arrivée en retard (une mesure plus récente existe) ;
- une mesure simultanée à une autre déjà enregistrée : température et
  occupation envoyées au même instant ne ferment qu'un seul intervalle.

Les intervalles sont idempotents : une observation relivrée par Kafka n'est
jamais comptée deux fois.

### Paramètres par défaut

| Type d'espace | Surface | Éclairage | Équipements fixes | Par personne | Occupation par défaut |
|---|---|---|---|---|---|
| Bureau | 20 m² | 8 W/m² | 150 W | 120 W | 1 |
| Salle de réunion | 30 m² | 10 W/m² | 100 W | 60 W | 2 |
| Cubicule | 6 m² | 8 W/m² | 50 W | 120 W | 1 |
| Espace ouvert | 80 m² | 8 W/m² | 300 W | 120 W | 4 |
| Salle de cours | 60 m² | 10 W/m² | 300 W | 40 W | 10 |
| Salle serveur | 25 m² | 5 W/m² | 4 000 W | 0 W | 0 |
| Laboratoire | 40 m² | 10 W/m² | 500 W | 150 W | 2 |
| Autre | 20 m² | 8 W/m² | 100 W | 100 W | 0 |

Pour tous : déperditions UA = 1 W/K par m² de plancher, air neuf 10 L/s par
personne, température extérieure de référence 5 °C, COP chauffage 2,5, COP
climatisation 3.

**À personnaliser en priorité** : la surface, les équipements fixes
(notamment la salle serveur) et la température extérieure de référence,
qui varie selon la saison.

## API

Voir [`api.md`](api.md#confort-thermique) et [`events.md`](events.md).
