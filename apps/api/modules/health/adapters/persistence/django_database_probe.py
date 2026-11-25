from django.db import connection


class DjangoDatabaseProbe:
    """Adaptateur Django du port ``DatabaseProbe`` : ``SELECT 1``."""

    def available(self) -> bool:
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
            return True
        except Exception:
            return False
