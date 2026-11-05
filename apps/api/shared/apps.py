from django.apps import AppConfig


class SharedConfig(AppConfig):
    """Noyau partagé : messagerie, contrats d'événements, HTTP commun.

    Ce n'est pas un module métier : il n'a ni modèle ni endpoint. Il est
    déclaré comme application Django uniquement pour fournir la commande
    ``run_consumers``.
    """

    name = "shared"
    verbose_name = "GRIDD — noyau partagé"
