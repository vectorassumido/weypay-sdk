"""Garante que providers/<x>/ nunca importa providers/<y>/ — é o que torna trivial extrair um
gateway para um pacote próprio mais tarde. Ver docs/ARCHITECTURE.md."""

import ast
from pathlib import Path

PROVIDERS_DIR = Path(__file__).resolve().parents[1] / "src" / "weypay" / "providers"


def _provider_names() -> list[str]:
    return sorted(p.name for p in PROVIDERS_DIR.iterdir() if p.is_dir())


def _imported_module_names(source: str) -> set[str]:
    tree = ast.parse(source)
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                names.add(alias.name)
    return names


def test_no_provider_imports_from_a_sibling_provider() -> None:
    providers = _provider_names()
    assert providers, (
        "nenhum provider encontrado — o teste ficaria vazio de propósito, não é o objetivo"
    )

    violations: list[str] = []
    for provider in providers:
        for py_file in (PROVIDERS_DIR / provider).rglob("*.py"):
            source = py_file.read_text()
            for module in _imported_module_names(source):
                for other in providers:
                    if other == provider:
                        continue
                    if f"providers.{other}" in module or module.startswith(f".{other}"):
                        violations.append(f"{py_file}: importa '{module}' (provider '{other}')")

    assert not violations, "\n".join(violations)
