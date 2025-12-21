# Kalima - Quran Research Platform

Tauri desktop application for Quranic text analysis, morphological research, and linguistic exploration.

## Quick Start

### Prerequisites
- Rust 1.77+ ([Install Rust](https://rustup.rs/))
- Tauri CLI: `cargo install tauri-cli --locked`
- Node.js (for E2E tests): see `docs/TESTING.md`
- Python 3 (optional; used for dataset scripts)

### Desktop App (no browser required)

**First-time setup** (after cloning repository):
```bash
cd Kalima

# Build the combined JSONL corpus (only needed once)
python scripts/build_combined_jsonl.py

# Ingest data into SQLite + Tantivy (only needed once)
cd engine
cargo run -p api --release --bin ingest -- --db ../data/database/kalima.db --index ../data/search-index --input ../datasets/combined.jsonl
cd ..
```

**Running the app:**
```bash
# Run desktop app directly from root
./Kalima.exe
```

**Development:**
```bash
# Develop with hot-reload
cd desktop/src-tauri
cargo tauri dev

# Build new executable
cd desktop/src-tauri
cargo tauri build
cp desktop/src-tauri/target/release/app.exe Kalima.exe
```

The desktop app automatically:
- Starts the Rust API server in-process
- Opens in a native window (no external browser)
- Loads data from `data/database/` and `data/search-index/` in the project directory

### CLI/Server Mode
```bash
# Clone repository
git clone https://github.com/wwwportal/Kalima.git
cd Kalima

# Build and run the API server (serves http://localhost:8080 by default)
cd engine
cargo run -p api --release
```

## Architecture

- **Backend:** Rust (Axum + SQLite + Tantivy)
  - 2,900 lines across 4 crates
  - 50+ REST endpoints
  - <1s startup, ~50MB memory
- **Frontend:** Vanilla JavaScript (runs in the Tauri WebView)
  - 17 modular files, no build system
  - Layered canvas architecture

## Features

- Browse 114 surahs, 6,236 verses
- Full-text search with Arabic diacritics
- Root-based morphological search
- Concordance search (Query Mode: `Q`, click tokens to build `#N key:value` patterns)
- POS pattern search
- Verb form analysis (Forms I-X)
- Dependency tree visualization
- Annotations & connections
- Hypothesis management
- Translation comparison

## API Endpoints

### Verse Navigation
- `GET /api/surahs` - List all surahs
- `GET /api/verse/:surah/:ayah` - Get specific verse
- `GET /api/surah/:number` - Get all verses in surah

### Search
- `GET /api/search?q=...` - Text search
- `GET /api/search/roots?root=...` - Root search
- `GET /api/search/morphology?q=...` - Morphology search
- `GET /api/search/verb_forms?form=IV` - Verb form search
- `POST /concordance` - Concordance search (sequential anchored patterns)

### Linguistic Data
- `GET /api/morphology/:surah/:ayah` - Morphological segments
- `GET /api/dependency/:surah/:ayah` - Dependency tree
- `GET /api/roots` - List all roots

### Research
- `GET /api/annotations/:surah/:ayah` - Annotations
- `POST /api/annotations/:surah/:ayah` - Create annotation
- `GET /api/hypotheses/:verse_ref` - Hypotheses
- `POST /api/hypotheses/:verse_ref` - Create hypothesis

## Deployment

### Docker
```bash
docker-compose up -d
```

### Systemd (Linux)
```bash
sudo cp deploy/kalima.service /etc/systemd/system/
sudo systemctl enable kalima
sudo systemctl start kalima
```

### Nginx Reverse Proxy
```bash
sudo cp deploy/nginx.conf /etc/nginx/sites-available/kalima
sudo ln -s /etc/nginx/sites-available/kalima /etc/nginx/sites-enabled/
sudo systemctl reload nginx
```

## Development

### Running Tests
```bash
npm run test:unit
cd desktop/src-tauri && cargo test
npm run test:e2e
```

### Code Quality
```bash
cargo clippy --all-targets
cargo fmt --all
```

## Performance

- **Startup:** <1 second
- **Search:** ~10-50ms
- **Memory:** ~50MB
- **Throughput:** >1000 req/s

## License

MIT OR Apache-2.0

## Credits

- Quranic Arabic Corpus Project
- MASAQ Morphological Dataset
- Quranic Treebank Project

## Docs

- Command laws/spec: `docs/COMMAND_LAWS.md`
- API contracts: `docs/API_CONTRACTS.md`
- Testing strategy: `docs/TESTING.md`
- Fixtures guidance: `docs/fixtures.md`
- Runbook (setup/test/troubleshoot): `docs/RUNBOOK.md`
