"""Pytest configuration for MCP server tests."""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


@pytest.fixture(scope="session")
def hf_token():
    """Get HuggingFace token if available."""
    import os
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
                repo_id="Syntra-Env/kalima-db",
                filename="kalima.db",
                repo_type="dataset",
                token=hf_token
            )
            shutil.copy(cached, db_path)
        else:
            cached = hf_hub_download(
                repo_id="Syntra-Env/kalima-db",
                filename="kalima.db",
                repo_type="dataset"
            )
            shutil.copy(cached, db_path)
    except Exception:
        # If download fails, tests will be skipped
        pytest.skip("Could not download test database")
    
    return str(db_path)
