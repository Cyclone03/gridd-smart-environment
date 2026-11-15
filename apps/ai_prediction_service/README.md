# GRIDD AI prediction service

Service Python indépendant. Cette première étape collecte les données; elle ne
charge pas les modèles, ne normalise pas les valeurs, ne publie pas sur Kafka
et ne programme pas de tâche périodique.

## Sources de données

- Open-Meteo : coordonnées obligatoires dans `OPEN_METEO_LATITUDE` et
  `OPEN_METEO_LONGITUDE`. Chaque appel récupère les conditions courantes et la
  prévision horaire pour la prochaine heure UTC complète.
- GRIDD : `GRIDD_API_BASE_URL` désigne l'API Django. Le client lit les zones
  actives sur `/api/zones/` puis leurs dernières observations sur
  `/api/observations/latest/`. Les codes sont ceux retournés par l'API, jamais
  déduits des noms `modelZone1` à `modelZone6`.

Le seed Django déclare actuellement les six codes `professors-office`,
`individual-work-cubicle-01`, `individual-work-cubicle-02`, `open-workspace`,
`meeting-room` et `server-equipment-room`. En exécution, l'API reste la source
de vérité : seules ses zones actives sont collectées. Le lien entre ces codes
et les modèles IA demeure à fournir.

## Configuration et utilisation

```text
GRIDD_API_BASE_URL=http://localhost:8000
OPEN_METEO_LATITUDE=45.5088
OPEN_METEO_LONGITUDE=-73.5878
HTTP_TIMEOUT_SECONDS=10
```

Le point d'entrée de collecte est `DataCollectionService.collect()`. Il peut
être appelé une fois par heure par le mécanisme d'exécution qui sera retenu.
Le dépôt ne fournit pas de planificateur Python adapté; cette étape n'en ajoute
pas. Les requêtes réseau ne sont pas mises en cache et chaque appel récupère
des données fraîches.

Les clients utilisent uniquement la bibliothèque standard Python. Pour lancer
les tests depuis la racine du dépôt sous PowerShell :

```powershell
$env:PYTHONPATH = (Join-Path (Get-Location) "apps\ai_prediction_service\src")
.\.venv\Scripts\python.exe -m unittest discover -s apps\ai_prediction_service\tests -v
```
