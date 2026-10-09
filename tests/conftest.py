"""Shared pytest fixtures for the entire test suite.

Fixtures declared here are visible to all tests under tests/.
Keep this file free of DB / FastAPI / docker dependencies.
"""
from __future__ import annotations

from pathlib import Path

import pytest

# Project root = parent of the tests/ directory
PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent

# In this project, domain/ and usecases/ live under app/
APP_DIR: Path = PROJECT_ROOT / "app"


@pytest.fixture(scope="session")
def project_root() -> Path:
    """Absolute path to the project root."""
    return PROJECT_ROOT


@pytest.fixture(scope="session")
def domain_dir() -> Path:
    """Absolute path to <project_root>/app/domain."""
    return APP_DIR / "domain"


@pytest.fixture(scope="session")
def usecases_dir() -> Path:
    """Absolute path to <project_root>/app/usecases."""
    return APP_DIR / "usecases"
