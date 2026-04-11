"""Pytest configuration for MCP server tests."""

import pytest
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


@pytest.fixture(scope="session")
def hf_token():
    """Get HuggingFace token if available."""
    return os.environ.get("HF_TOKEN")


@pytest.fixture(scope="session")
def test_db_path(tmp_path_factory, hf_token):
    """Download or create a test database."""
    import shutil
    from huggingface_hub import hf_hub_download
    
    db_path = tmp_path_factory.mktemp("db") / "kalima.db"
    
    try:
        # Try to download from HuggingFace
        if hf_token:
            cached = hf_hub_download(
                repo_id="Syntra-Lab/kalima-db",
                filename="kalima.db",
                repo_type="dataset",
                token=hf_token
            )
        else:
            cached = hf_hub_download(
                repo_id="Syntra-Lab/kalima-db",
                filename="kalima.db",
                repo_type="dataset"
            )
        shutil.copy(cached, db_path)
        return str(db_path)
    except Exception as e:
        # If download fails, skip the tests that need the DB
        pytest.skip(f"Could not download test database: {e}")
