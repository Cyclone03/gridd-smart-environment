"""Noyau partagé pur (Python standard uniquement).

Vocabulaire commun à tous les modules : enveloppe d'événement, types
d'événements, catalogue des mesures, périodes d'analyse, statuts partagés et
utilitaires d'horodatage. Aucun import de Django, DRF, Channels ou Kafka :
le cœur (``core/``) de chaque module peut l'utiliser et rester réutilisable
dans un autre projet. Copier ``shared/kernel`` suffit à transporter ce
vocabulaire.
"""
