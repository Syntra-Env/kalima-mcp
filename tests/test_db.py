"""Tests for database module."""
import pytest
import sqlite3
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.db import (
    get_connection,
    close_database,
    HF_REPO_ID,
    DEFAULT_DB_PATH,
)


@pytest.fixture(autouse=True)
def fresh_connection():
    """Reset connection before each test."""
    import src.db as db_module
    db_module._conn = None
    yield
    db_module._conn = None


@pytest.fixture
def temp_db(tmp_path):
    """Create a temp database file and return its path."""
    db_file = tmp_path / "test.db"
    yield str(db_file)
    # Cleanup - close connection first
    import src.db as db_module
    db_module._conn = None


class TestDatabaseConnection:
    """Test database connection functionality."""

    def test_connection_creates_tables(self, temp_db, monkeypatch):
        """Test that connection creates core tables."""
        monkeypatch.setenv("KALIMA_DB_PATH", temp_db)
        
        conn = get_connection()
        
        # Check expected tables exist (only ones created by init functions)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row[0] for row in cursor.fetchall()}
        
        expected_tables = {
            "features",
            "holonomic_entries",
            "content_addresses",
            "traditional_interpretations",
            "root_vectors",
        }
        assert expected_tables.issubset(tables), f"Missing tables: {expected_tables - tables}"

    def test_connection_sets_row_factory(self, temp_db, monkeypatch):
        """Test that rows are returned as Row objects."""
        monkeypatch.setenv("KALIMA_DB_PATH", temp_db)
        
        conn = get_connection()
        cursor = conn.cursor()
        
        # Insert test data first
        cursor.execute("""
            INSERT INTO features (feature_type, category, lookup_key, label_en)
            VALUES (?, ?, ?, ?)
        """, ("root", "test", "test_key", "test label"))
        
        cursor.execute("SELECT * FROM features LIMIT 1")
        row = cursor.fetchone()
        
        assert row is not None
        assert hasattr(row, 'keys')
        assert row['lookup_key'] == 'test_key'

    def test_foreign_keys_enabled(self, temp_db, monkeypatch):
        """Test that foreign keys are enforced."""
        monkeypatch.setenv("KALIMA_DB_PATH", temp_db)
        
        conn = get_connection()
        cursor = conn.cursor()
        
        # Check PRAGMA
        cursor.execute("PRAGMA foreign_keys")
        result = cursor.fetchone()[0]
        assert result == 1, "Foreign keys should be enabled"

    def test_wal_mode_enabled(self, temp_db, monkeypatch):
        """Test that delete journal mode is set (WAL disabled to reduce CPU overhead)."""
        monkeypatch.setenv("KALIMA_DB_PATH", temp_db)
        
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("PRAGMA journal_mode")
        result = cursor.fetchone()[0]
        assert result == "delete", f"Expected delete mode, got {result}"


class TestFeaturesTable:
    """Test features table functionality."""

    def test_insert_and_retrieve_feature(self, temp_db, monkeypatch):
        """Test inserting and retrieving a feature."""
        monkeypatch.setenv("KALIMA_DB_PATH", temp_db)
        conn = get_connection()
        cursor = conn.cursor()
        
        # Insert a feature
        cursor.execute("""
            INSERT INTO features (feature_type, category, lookup_key, label_en)
            VALUES (?, ?, ?, ?)
        """, ("root", "test", "ك-ت-ب", "to write"))
        
        # Retrieve it
        cursor.execute("""
            SELECT * FROM features WHERE lookup_key = ?
        """, ("ك-ت-ب",))
        row = cursor.fetchone()
        
        assert row is not None
        assert row["feature_type"] == "root"
        assert row["lookup_key"] == "ك-ت-ب"

    def test_feature_uniqueness(self, temp_db, monkeypatch):
        """Test that feature_type/category/lookup_key is unique."""
        monkeypatch.setenv("KALIMA_DB_PATH", temp_db)
        conn = get_connection()
        cursor = conn.cursor()
        
        # Insert first
        cursor.execute("""
            INSERT INTO features (feature_type, category, lookup_key)
            VALUES (?, ?, ?)
        """, ("root", "test", "unique_key"))
        
        # Try duplicate - should fail
        with pytest.raises(sqlite3.IntegrityError):
            cursor.execute("""
                INSERT INTO features (feature_type, category, lookup_key)
                VALUES (?, ?, ?)
            """, ("root", "test", "unique_key"))


class TestHolonomicEntries:
    """Test holonomic_entries table functionality."""

    def test_insert_entry(self, temp_db, monkeypatch):
        """Test inserting a holonomic entry."""
        monkeypatch.setenv("KALIMA_DB_PATH", temp_db)
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO holonomic_entries 
            (address, content, phase, category, anchor_type, anchor_ids)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            "abc123",
            "Test content about Ibrahim",
            "question",
            "methodology",
            "root",
            "1"
        ))
        
        # Retrieve
        cursor.execute("SELECT * FROM holonomic_entries WHERE address = ?", ("abc123",))
        row = cursor.fetchone()
        
        assert row is not None
        assert row["phase"] == "question"
        assert row["category"] == "methodology"

    def test_entry_with_verification(self, temp_db, monkeypatch):
        """Test entry with verification status."""
        monkeypatch.setenv("KALIMA_DB_PATH", temp_db)
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO holonomic_entries 
            (address, content, verification, confidence)
            VALUES (?, ?, ?, ?)
        """, (
            "def456",
            "Entry with verification",
            "supports",
            0.85
        ))
        
        cursor.execute("SELECT * FROM holonomic_entries WHERE address = ?", ("def456",))
        row = cursor.fetchone()
        
        assert row["verification"] == "supports"
        assert row["confidence"] == 0.85


class TestContentAddresses:
    """Test content_addresses table for UOR."""

    def test_insert_address_mapping(self, temp_db, monkeypatch):
        """Test inserting a content address mapping."""
        monkeypatch.setenv("KALIMA_DB_PATH", temp_db)
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO content_addresses 
            (entity_type, entity_id, address)
            VALUES (?, ?, ?)
        """, ("verse", "1:1", "sha256_abc"))
        
        cursor.execute("SELECT * FROM content_addresses WHERE entity_id = ?", ("1:1",))
        row = cursor.fetchone()
        
        assert row is not None
        assert row["entity_type"] == "verse"


class TestIndexes:
    """Test that required indexes exist."""

    def test_features_indexes(self, temp_db, monkeypatch):
        """Test features table indexes."""
        monkeypatch.setenv("KALIMA_DB_PATH", temp_db)
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='features'")
        indexes = {row[0] for row in cursor.fetchall()}
        
        assert "idx_features_type" in indexes
        assert "idx_features_lookup" in indexes

    def test_holonomic_entries_indexes(self, temp_db, monkeypatch):
        """Test holonomic_entries table indexes."""
        monkeypatch.setenv("KALIMA_DB_PATH", temp_db)
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='holonomic_entries'")
        indexes = {row[0] for row in cursor.fetchall()}
        
        assert "idx_he_anchor" in indexes
        assert "idx_he_activity" in indexes
        assert "idx_he_category" in indexes


class TestHFConfig:
    """Test HuggingFace configuration."""

    def test_hf_repo_id(self):
        """Test HF repo ID is set correctly."""
        assert HF_REPO_ID == "Syntra-Lab/kalima-db"

    def test_default_db_path(self):
        """Test default DB path is in user home."""
        assert str(DEFAULT_DB_PATH).startswith(str(Path.home()))
        assert "kalima" in str(DEFAULT_DB_PATH)
