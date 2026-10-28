"""Authentification par jeton à durée de vie limitée.

Le frontend est déployé sur un autre domaine que l'API : un jeton transmis
dans l'en-tête ``Authorization: Token <clé>`` évite la gestion des cookies
inter-domaines et du CSRF. Le jeton expire après ``AUTH_TOKEN_TTL_HOURS``
et est renouvelé à chaque connexion.
"""

from datetime import timedelta

from django.conf import settings
from django.utils import timezone
from rest_framework.authentication import TokenAuthentication
from rest_framework.authtoken.models import Token
from rest_framework.exceptions import AuthenticationFailed


def token_expires_at(token):
    return token.created + timedelta(hours=settings.AUTH_TOKEN_TTL_HOURS)


def issue_token(user):
    """Remplace le jeton existant de l'utilisateur par un nouveau."""
    Token.objects.filter(user=user).delete()
    return Token.objects.create(user=user)


class ExpiringTokenAuthentication(TokenAuthentication):
    def authenticate_credentials(self, key):
        user, token = super().authenticate_credentials(key)
        if timezone.now() >= token_expires_at(token):
            token.delete()
            raise AuthenticationFailed("Session expirée. Veuillez vous reconnecter.")
        return user, token
