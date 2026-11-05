import logging

from rest_framework import status
from rest_framework.exceptions import APIException, NotFound, ValidationError
from rest_framework.response import Response
from rest_framework.views import exception_handler

from shared.messaging import CommandFailed, MessagingUnavailable
from shared.periods import PeriodParamError

from .service_unavailable import ServiceUnavailable

logger = logging.getLogger(__name__)


class ApiExceptionHandler:
    """Format d'erreur uniforme de l'API.

    Toutes les réponses d'erreur ont la forme :

        {"detail": "Message lisible", "errors": {"champ": ["message", ...]}}

    ``errors`` n'est présent que pour les erreurs de validation. Les erreurs
    de messagerie sont aussi traduites ici, pour que les contrôleurs n'aient
    aucune logique de gestion d'erreur :

    - commande refusée par le module destinataire → 404, 400 ou 500 ;
    - Kafka ou module injoignable, pas de réponse → 503.

    Une erreur de période renvoie son propre message dans ``detail``.
    """

    def __call__(self, exc, context):
        if isinstance(exc, PeriodParamError):
            body = {"detail": exc.message}
            if exc.field:
                body["errors"] = {exc.field: [exc.field_message]}
            return Response(body, status=status.HTTP_400_BAD_REQUEST)
        response = exception_handler(self._translate(exc), context)
        if response is None:
            return None

        if isinstance(exc, (ValidationError, CommandFailed)) and response.status_code == 400:
            data = response.data
            if isinstance(data, list):
                data = {"non_field_errors": data}
            response.data = {"detail": "Certaines données sont invalides.", "errors": data}
        elif isinstance(response.data, dict) and "detail" in response.data:
            response.data = {"detail": str(response.data["detail"])}
        return response

    @staticmethod
    def _translate(exc):
        if isinstance(exc, CommandFailed):
            if exc.code == CommandFailed.NOT_FOUND:
                return NotFound(exc.message)
            if exc.code == CommandFailed.INVALID:
                return ValidationError(exc.errors or {"non_field_errors": [exc.message]})
            return APIException(exc.message)
        if isinstance(exc, MessagingUnavailable):
            # Le client reçoit un message générique ; la cause reste dans les journaux.
            logger.warning("Réponse 503 — %s : %s", type(exc).__name__, exc)
            return ServiceUnavailable()
        return exc


# Point d'entrée référencé par REST_FRAMEWORK["EXCEPTION_HANDLER"].
api_exception_handler = ApiExceptionHandler()
