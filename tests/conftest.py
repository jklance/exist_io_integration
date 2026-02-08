"""Shared pytest fixtures."""

import json
import sqlite3
from pathlib import Path

import pytest

from exist_backup import db

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def sample_profile():
    with open(FIXTURES_DIR / "profile.json") as f:
        return json.load(f)


@pytest.fixture
def sample_attributes():
    with open(FIXTURES_DIR / "attributes.json") as f:
        return json.load(f)


@pytest.fixture
def sample_values():
    with open(FIXTURES_DIR / "values.json") as f:
        return json.load(f)


@pytest.fixture
def test_db(tmp_path):
    """Create an in-memory-like temp database, initialized with schema."""
    db_path = str(tmp_path / "test.db")
    conn = db.connect(db_path)
    db.init_db(conn)
    yield conn
    conn.close()


@pytest.fixture
def populated_db(test_db, sample_profile, sample_attributes, sample_values):
    """Database pre-populated with sample data."""
    db.upsert_profile(test_db, sample_profile)
    for attr in sample_attributes:
        db.upsert_attribute(test_db, attr)
    for val in sample_values:
        db.upsert_values(test_db, val["name"], val["values"])
    return test_db
