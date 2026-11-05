from collections.abc import Callable
from dataclasses import dataclass

from .message_handler import MessageHandler


@dataclass(frozen=True)
class Subscription:
    """Abonnement d'un module à un ensemble de topics.

    - ``name`` : identifiant du module ; avec Kafka, il sert de suffixe au
      consumer group, si bien que chaque module reçoit tous les messages de
      ses topics, indépendamment des autres modules ;
    - ``handler_factory`` : construit le gestionnaire au démarrage du
      consommateur (aucun accès base au chargement de Django) ;
    - ``connection`` : connexion Kafka à utiliser (``main`` ou ``sensors``) ;
    - ``start_at_live_edge`` : ignorer l'arriéré et ne lire que les nouveaux
      messages (temps réel capteurs), sauf ``--replay-backlog``.
    """

    name: str
    topics: tuple[str, ...]
    handler_factory: Callable[[], MessageHandler]
    connection: str = "main"
    start_at_live_edge: bool = False
