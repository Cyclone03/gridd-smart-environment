"""Règles d'architecture, vérifiées à chaque exécution des tests.

1. Un fichier = une classe (au plus une classe de premier niveau).
2. Les modules ne dépendent pas les uns des autres : ils n'importent que
   leur propre code, le noyau ``shared`` et le schéma ``modules.database.models``
   (lecture seule). Ils communiquent par Kafka.
3. Seul le module Database écrit en base.
4. Les contrôleurs ne contiennent ni accès aux données ni logique métier :
   ils délèguent à un service.
"""

import ast
from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase

ROOT = Path(settings.BASE_DIR)
MODULES = ROOT / "modules"
EXCLUDED_PARTS = {"migrations", "tests", "__pycache__"}

# Méthodes ORM d'écriture : toujours suspectes, ou seulement sur un manager / queryset.
ALWAYS_WRITES = {"save", "delete", "bulk_create", "bulk_update", "get_or_create", "update_or_create"}
QUERYSET_WRITES = {"create", "update"}


def source_files(base):
    for path in sorted(base.rglob("*.py")):
        if not EXCLUDED_PARTS.intersection(path.relative_to(ROOT).parts):
            yield path


def orm_writes(tree):
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            method, receiver = node.func.attr, ast.unparse(node.func.value)
            if method in ALWAYS_WRITES or (method in QUERYSET_WRITES and "objects" in receiver):
                yield node.lineno, f"{receiver}.{method}(…)"


def imported_modules(tree):
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            yield from (alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            yield node.module


class ArchitectureTests(SimpleTestCase):
    def test_one_class_per_file(self):
        offenders = []
        for path in [*source_files(MODULES), *source_files(ROOT / "shared")]:
            classes = [node.name for node in ast.parse(path.read_text()).body if isinstance(node, ast.ClassDef)]
            if len(classes) > 1:
                offenders.append(f"{path.relative_to(ROOT)} : {', '.join(classes)}")
        self.assertEqual(offenders, [], "Plusieurs classes dans un même fichier")

    def test_modules_do_not_import_each_other(self):
        offenders = []
        for module_dir in sorted(path for path in MODULES.iterdir() if path.is_dir() and path.name != "__pycache__"):
            own = f"modules.{module_dir.name}"
            for path in source_files(module_dir):
                for name in imported_modules(ast.parse(path.read_text())):
                    if not name.startswith("modules."):
                        continue
                    if name == own or name.startswith(own + ".") or name == "modules.database.models":
                        continue
                    offenders.append(f"{path.relative_to(ROOT)} → {name}")
        self.assertEqual(offenders, [], "Dépendance directe entre modules")

    def test_only_the_database_module_writes(self):
        offenders = []
        for module_dir in sorted(path for path in MODULES.iterdir() if path.is_dir() and path.name != "database"):
            for path in source_files(module_dir):
                for number, call in orm_writes(ast.parse(path.read_text())):
                    offenders.append(f"{path.relative_to(ROOT)}:{number} {call}")
        self.assertEqual(offenders, [], "Écriture en base hors du module Database")

    def test_controllers_delegate_to_services(self):
        offenders = []
        for path in MODULES.glob("*/controllers/*.py"):
            if path.name == "__init__.py":
                continue
            for name in imported_modules(ast.parse(path.read_text())):
                if ".repositories." in name or ".writers." in name or name.startswith("django.db"):
                    offenders.append(f"{path.relative_to(ROOT)} → {name}")
        self.assertEqual(offenders, [], "Un contrôleur accède directement aux données")
