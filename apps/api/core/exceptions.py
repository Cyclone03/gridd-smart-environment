"""Format d'erreur uniforme de l'API.

Toutes les réponses d'erreur ont la forme :

    {"detail": "Message lisible", "errors": {"champ": ["message", ...]}}

``errors`` n'est présent que pour les erreurs de validation. Le frontend
affiche ``detail`` et associe ``errors`` aux champs de formulaire.
"""

from rest_framework.exceptions import ValidationError
from rest_framework.views import exception_handler


def api_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is None:
        return None

    if isinstance(exc, ValidationError):
        data = response.data
        if isinstance(data, list):
            data = {"non_field_errors": data}
        response.data = {
            "detail": "Certaines données sont invalides.",
            "errors": data,
        }
    elif isinstance(response.data, dict) and "detail" in response.data:
        response.data = {"detail": str(response.data["detail"])}

    return response
