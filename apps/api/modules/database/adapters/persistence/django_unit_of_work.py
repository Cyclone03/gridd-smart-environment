from django.db import transaction


class DjangoUnitOfWork:
    """Adaptateur Django du port ``UnitOfWork``."""

    def atomic(self):
        return transaction.atomic()
