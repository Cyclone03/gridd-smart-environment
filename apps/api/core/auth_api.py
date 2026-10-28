"""Authentification : ``/api/auth/token/``, ``/api/auth/me/``, ``/api/auth/logout/``.

Les comptes sont gérés dans l'admin Django (ou ``createsuperuser``). Les
droits sur les règles d'alarme s'obtiennent via le groupe « Gestionnaires des
alarmes » ou les permissions ``core.*_alarmrule``.
"""

from django.contrib.auth import authenticate
from rest_framework import serializers, status
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle

from .authentication import issue_token, token_expires_at
from .permissions import alarm_rule_permissions_for


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField(error_messages={"blank": "L'identifiant est obligatoire."})
    password = serializers.CharField(
        trim_whitespace=False,
        error_messages={"blank": "Le mot de passe est obligatoire."},
    )


def user_payload(user):
    return {
        "username": user.get_username(),
        "display_name": user.get_full_name() or user.get_username(),
        "is_staff": user.is_staff,
        "permissions": {"alarm_rules": alarm_rule_permissions_for(user)},
    }


class LoginThrottle(AnonRateThrottle):
    """Limite les tentatives de connexion par adresse IP (LOGIN_THROTTLE_RATE)."""

    scope = "login"


@api_view(["POST"])
@permission_classes([AllowAny])
@throttle_classes([LoginThrottle])
def obtain_token(request):
    serializer = LoginSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    user = authenticate(
        request,
        username=serializer.validated_data["username"],
        password=serializer.validated_data["password"],
    )
    if user is None or not user.is_active:
        raise AuthenticationFailed("Identifiant ou mot de passe incorrect.")
    token = issue_token(user)
    return Response(
        {
            "token": token.key,
            "expires_at": token_expires_at(token).isoformat(),
            "user": user_payload(user),
        }
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def me(request):
    return Response(user_payload(request.user))


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def logout(request):
    if request.auth is not None and hasattr(request.auth, "delete"):
        request.auth.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)
