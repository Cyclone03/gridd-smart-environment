from shared.module_config import ModuleConfig


class IaConfig(ModuleConfig):
    """Module IA : prédictions climatiques H+1 par zone (modèles Keras) et
    instantané météo Open-Meteo, publiés sur le bus d'événements.

    Aucun abonnement Kafka : le module est piloté par son planificateur
    (``python manage.py run_ai_predictions``), exécuté dans l'image Docker
    dédiée (cible ``ia``). L'importer ne charge ni TensorFlow ni numpy.
    """

    name = "modules.ia"
    label = "ia"
    verbose_name = "GRIDD — prédictions IA"
