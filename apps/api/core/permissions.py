from django.contrib.auth.models import Group, Permission
from rest_framework.permissions import SAFE_METHODS, DjangoModelPermissions


ALARM_MANAGERS_GROUP = "Gestionnaires des alarmes"

ALARM_RULE_PERMISSIONS = (
    "view_alarmrule",
    "add_alarmrule",
    "change_alarmrule",
    "delete_alarmrule",
)


class PublicReadModelPermissions(DjangoModelPermissions):
    """Lecture publique, écriture soumise aux permissions Django du modèle.

    - GET/HEAD/OPTIONS : autorisés à tous (le tableau de bord est en lecture
      libre, comme le reste de l'API).
    - POST : ``core.add_<modèle>`` ; PATCH/PUT : ``core.change_<modèle>`` ;
      DELETE : ``core.delete_<modèle>``. Un utilisateur anonyme reçoit 401.
    """

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        return super().has_permission(request, view)


def alarm_rule_permissions_for(user):
    """Droits exposés au frontend pour adapter l'interface."""
    authenticated = bool(user and user.is_authenticated)
    return {
        "add": authenticated and user.has_perm("core.add_alarmrule"),
        "change": authenticated and user.has_perm("core.change_alarmrule"),
        "delete": authenticated and user.has_perm("core.delete_alarmrule"),
    }


def ensure_alarm_managers_group(**kwargs):
    """Crée (ou complète) le groupe des gestionnaires d'alarmes.

    Appelé après chaque ``migrate`` : les permissions Django n'existent
    qu'une fois les migrations appliquées.
    """
    permissions = Permission.objects.filter(
        content_type__app_label="core",
        codename__in=ALARM_RULE_PERMISSIONS,
    )
    if permissions.count() != len(ALARM_RULE_PERMISSIONS):
        return
    group, _ = Group.objects.get_or_create(name=ALARM_MANAGERS_GROUP)
    group.permissions.add(*permissions)
