#!/usr/bin/env python3
"""Download scholar.db from HuggingFace."""
from huggingface_hub import hf_hub_download

db_path = hf_hub_download(repo_id="Syntra-Env/scholar-db", filename="kalima.db", repo_type="dataset")
print(f"Database downloaded to: {db_path}")
