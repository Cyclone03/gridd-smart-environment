from rest_framework import status
from rest_framework.exceptions import APIException


class ServiceUnavailable(APIException):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    default_detail = "Service momentanément indisponible. Réessayez dans quelques instants."
    default_code = "service_unavailable"
