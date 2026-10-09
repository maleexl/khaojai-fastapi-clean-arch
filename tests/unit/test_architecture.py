"""Architecture tests using `ast` to enforce Clean Architecture boundaries.

These are the "selling point" tests of the project: they prove with code
(not prose) that:

    - the domain layer stays pure (no framework, ORM, or validation libs)
    - the usecase layer depends only on the domain layer — never on the
      concrete interface / infrastructure implementations

A violation is reported with file path, line number, the offending import
string, and which forbidden segment(s) it matched.
"""
from __future__ import annotations

import ast
from pathlib import Path

DOMAIN_FORBIDDEN: frozenset[str] = frozenset(
    {"fastapi", "sqlalchemy", "pydantic", "jose", "bcrypt"}
)
USECASES_FORBIDDEN: frozenset[str] = frozenset(
    {"fastapi", "sqlalchemy", "pydantic", "interface", "infrastructure"}
)

_PROJECT_ROOT: Path = Path(__file__).resolve().parents[2]


def _iter_python_files(directory: Path) -> list[Path]:
    """All .py files under `directory`, recursively, skipping __pycache__."""
    return sorted(
        p for p in directory.rglob("*.py") if "__pycache__" not in p.parts
    )


def _collect_imports(path: Path) -> list[tuple[str, int]]:
    """Return [(dotted_module, lineno), ...] for every import in `path`."""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    collected: list[tuple[str, int]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                collected.append((alias.name, node.lineno))
        elif isinstance(node, ast.ImportFrom):
            if node.module is None:
                continue
            collected.append((node.module, node.lineno))
    return collected


def _violations(directory: Path, forbidden: frozenset[str]) -> list[str]:
    """Return human-readable violations under `directory`."""
    problems: list[str] = []
    for path in _iter_python_files(directory):
        for dotted, lineno in _collect_imports(path):
            hits = set(dotted.split(".")) & forbidden
            if hits:
                try:
                    rel = path.relative_to(_PROJECT_ROOT)
                except ValueError:
                    rel = path
                problems.append(
                    f"  {rel}:{lineno} imports '{dotted}' "
                    f"(forbidden segment(s): {sorted(hits)})"
                )
    return problems


def test_domain_layer_has_no_framework_imports(domain_dir: Path) -> None:
    """domain/ must stay pure — no FastAPI, SQLAlchemy, Pydantic, jose, bcrypt."""
    assert domain_dir.is_dir(), f"domain directory not found: {domain_dir}"

    files = _iter_python_files(domain_dir)
    assert files, f"no Python files found under {domain_dir}"

    problems = _violations(domain_dir, DOMAIN_FORBIDDEN)
    assert not problems, (
        "Domain layer imports forbidden modules (Clean Architecture violation):\n"
        + "\n".join(problems)
    )


def test_usecase_layer_does_not_import_outer_layers(usecases_dir: Path) -> None:
    """usecases/ must depend only on domain + shared."""
    assert usecases_dir.is_dir(), f"usecases directory not found: {usecases_dir}"

    files = _iter_python_files(usecases_dir)
    assert files, f"no Python files found under {usecases_dir}"

    problems = _violations(usecases_dir, USECASES_FORBIDDEN)
    assert not problems, (
        "Usecase layer imports forbidden modules "
        "(would break Dependency Inversion):\n" + "\n".join(problems)
    )


def test_scan_covers_expected_files(domain_dir: Path, usecases_dir: Path) -> None:
    """Sanity check: the scanner sees the files we expect."""
    domain_files = {p.name for p in _iter_python_files(domain_dir)}
    usecase_files = {p.name for p in _iter_python_files(usecases_dir)}

    assert "user.py" in domain_files
    assert "user_repository.py" in domain_files
    assert "token_blacklist_repository.py" in domain_files
    assert "user_usecase.py" in usecase_files


def test_import_collector_detects_forbidden_import(tmp_path: Path) -> None:
    """Self-test: prove the AST checker actually detects violations."""
    sample = tmp_path / "bad.py"
    sample.write_text(
        "import fastapi\n"
        "from sqlalchemy.orm import Session\n"
        "from pydantic import BaseModel\n"
        "from app.interface.repositories import Something\n"
        "from app.infrastructure.database import engine\n",
        encoding="utf-8",
    )

    collected = {name for name, _ in _collect_imports(sample)}
    assert "fastapi" in collected
    assert "sqlalchemy.orm" in collected
    assert "pydantic" in collected
    assert "app.interface.repositories" in collected
    assert "app.infrastructure.database" in collected

    domain_hits = _violations(tmp_path, DOMAIN_FORBIDDEN)
    joined_domain = "\n".join(domain_hits)
    assert "fastapi" in joined_domain
    assert "sqlalchemy" in joined_domain
    assert "pydantic" in joined_domain
    assert "interface" not in joined_domain
    assert "infrastructure" not in joined_domain

    usecase_hits = _violations(tmp_path, USECASES_FORBIDDEN)
    joined_uc = "\n".join(usecase_hits)
    assert "app.interface.repositories" in joined_uc
    assert "app.infrastructure.database" in joined_uc
