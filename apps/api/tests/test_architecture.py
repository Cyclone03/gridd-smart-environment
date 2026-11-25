"""Règles d'architecture, vérifiées à chaque exécution des tests.

Chaque module (``modules/<nom>/``) est autonome et réutilisable :

- ``core/`` (domaine, ports, services) est du Python pur : ni Django, ni DRF,
  ni Channels, ni Kafka, ni autre module, ni infrastructure ``shared``. Il ne
  dépend que de la bibliothèque standard, de bibliothèques de calcul et du
  noyau pur ``shared.kernel`` ;
- ``adapters/`` relie le cœur au projet hôte (ORM, Kafka, HTTP, WebSocket) ;
- ``composition.py`` assemble le cœur et les adaptateurs ; ``apps.py``
  déclare le module à Django ;
- ``README.md`` décrit le contrat d'intégration du module.

Règles :

1. Un fichier = une classe (au plus une classe de premier niveau).
2. Les modules ne dépendent pas les uns des autres : ils n'importent que leur
   propre code, ``shared`` et le schéma ``modules.database.models`` (lecture
   seule, depuis leurs adaptateurs uniquement). Ils communiquent par Kafka.
3. Le cœur d'un module est indépendant du framework et des autres modules.
4. Le noyau ``shared.kernel`` n'importe que la bibliothèque standard.
5. Seul le module Database écrit en base.
6. Les contrôleurs ne contiennent ni accès aux données ni logique métier :
   ils délèguent à un service obtenu par la racine de composition.
7. Chaque module a la structure attendue.
"""

import ast
import subprocess
import sys
from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase

ROOT = Path(settings.BASE_DIR)
MODULES = ROOT / "modules"
KERNEL = ROOT / "shared" / "kernel"
EXCLUDED_PARTS = {"migrations", "tests", "__pycache__", "artifacts"}

# Méthodes ORM d'écriture : toujours suspectes, ou seulement sur un manager / queryset.
ALWAYS_WRITES = {"save", "delete", "bulk_create", "bulk_update", "get_or_create", "update_or_create"}
QUERYSET_WRITES = {"create", "update"}

# Interdits dans un cœur : frameworks et infrastructure du projet hôte.
FRAMEWORKS = ("django", "rest_framework", "channels", "asgiref", "daphne", "confluent_kafka", "redis", "psycopg")
REQUIRED_ENTRIES = ("README.md", "apps.py", "composition.py", "core/__init__.py", "adapters/__init__.py")


def module_dirs():
    return sorted(path for path in MODULES.iterdir() if path.is_dir() and (path / "apps.py").exists())


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


def imported_modules(path):
    """Modules importés, imports relatifs résolus en noms absolus."""
    package = ".".join(path.relative_to(ROOT).with_suffix("").parts[:-1])
    for node in ast.walk(ast.parse(path.read_text())):
        if isinstance(node, ast.Import):
            yield from (alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.level == 0:
                yield node.module
            else:
                base = package.split(".")[: len(package.split(".")) - node.level + 1]
                yield ".".join([*base, node.module] if node.module else base)


def is_within(name, prefix):
    return name == prefix or name.startswith(prefix + ".")


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
        for module_dir in module_dirs():
            own = f"modules.{module_dir.name}"
            for path in source_files(module_dir):
                in_core = "core" in path.relative_to(module_dir).parts
                for name in imported_modules(path):
                    if not is_within(name, "modules") or is_within(name, own):
                        continue
                    if name == "modules.database.models" and not in_core:
                        continue
                    offenders.append(f"{path.relative_to(ROOT)} → {name}")
        self.assertEqual(offenders, [], "Dépendance directe entre modules")

    def test_core_is_framework_independent(self):
        offenders = []
        for module_dir in module_dirs():
            own_core = f"modules.{module_dir.name}.core"
            core = module_dir / "core"
            if not core.exists():
                continue
            for path in source_files(core):
                for name in imported_modules(path):
                    forbidden = (
                        name.split(".")[0] in FRAMEWORKS
                        or (is_within(name, "modules") and not is_within(name, own_core))
                        or (is_within(name, "shared") and not is_within(name, "shared.kernel"))
                    )
                    if forbidden:
                        offenders.append(f"{path.relative_to(ROOT)} → {name}")
        self.assertEqual(offenders, [], "Le cœur d'un module dépend du framework ou d'un autre module")

    def test_cores_import_without_any_framework(self):
        """Chaque cœur (et le noyau) s'importe dans un interpréteur où Django,
        DRF, Channels et Kafka sont introuvables : preuve qu'il est portable."""
        packages = sorted(
            ".".join(path.relative_to(ROOT).with_suffix("").parts)
            for base in [KERNEL, *(module_dir / "core" for module_dir in module_dirs())]
            for path in source_files(base)
            if path.name != "__init__.py"
        )
        script = (
            "import importlib, importlib.abc, sys\n"
            f"sys.path.insert(0, {str(ROOT)!r})\n"
            "class Block(importlib.abc.MetaPathFinder):\n"
            "    def find_spec(self, name, path=None, target=None):\n"
            f"        if name.split('.')[0] in {FRAMEWORKS!r}:\n"
            "            raise ImportError(f'framework interdit dans un cœur : {name}')\n"
            "sys.meta_path.insert(0, Block())\n"
            f"for name in {packages!r}:\n"
            "    importlib.import_module(name)\n"
        )
        result = subprocess.run(
            [sys.executable, "-I", "-c", script], cwd=ROOT, capture_output=True, text=True
        )
        self.assertEqual(result.returncode, 0, result.stderr[-2000:])

    def test_kernel_only_uses_the_standard_library(self):
        offenders = []
        for path in source_files(KERNEL):
            for name in imported_modules(path):
                top = name.split(".")[0]
                if top not in sys.stdlib_module_names and not is_within(name, "shared.kernel"):
                    offenders.append(f"{path.relative_to(ROOT)} → {name}")
        self.assertEqual(offenders, [], "Le noyau partagé importe autre chose que la bibliothèque standard")

    def test_only_the_database_module_writes(self):
        offenders = []
        for module_dir in module_dirs():
            if module_dir.name == "database":
                continue
            for path in source_files(module_dir):
                for number, call in orm_writes(ast.parse(path.read_text())):
                    offenders.append(f"{path.relative_to(ROOT)}:{number} {call}")
        self.assertEqual(offenders, [], "Écriture en base hors du module Database")

    def test_controllers_delegate_to_services(self):
        offenders = []
        for path in MODULES.glob("*/adapters/http/*_controller.py"):
            for name in imported_modules(path):
                if ".adapters.persistence" in name or is_within(name, "django.db") or name.endswith(".models"):
                    offenders.append(f"{path.relative_to(ROOT)} → {name}")
        self.assertEqual(offenders, [], "Un contrôleur accède directement aux données")

    def test_modules_have_the_expected_structure(self):
        missing = [
            f"modules/{module_dir.name}/{entry}"
            for module_dir in module_dirs()
            for entry in REQUIRED_ENTRIES
            if not (module_dir / entry).exists()
        ]
        self.assertEqual(missing, [], "Structure de module incomplète")

    def test_every_installed_module_is_checked(self):
        installed = {app.split(".")[1] for app in settings.INSTALLED_APPS if app.startswith("modules.")}
        self.assertEqual(installed, {path.name for path in module_dirs()})
