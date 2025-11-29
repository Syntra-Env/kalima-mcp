# Kalima - Quranic Research Platform

High-performance web application for Quranic text analysis, morphological research, and linguistic exploration.

## Quick Start

### Prerequisites
- Rust 1.70+ ([Install Rust](https://rustup.rs/))
- Tauri CLI: `cargo install tauri-cli --locked`

### Desktop App (no browser required)

**First-time setup** (after cloning repository):
```bash
cd Kalima

# Build and run data ingestion (only needed once)
cd engine
cargo run --release --bin ingest -- --db ../kalima.db --index ../kalima-index --input ../datasets/corpus/quran.jsonl
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
cargo tauri dev

# Build new executable
cargo tauri build
cp src-tauri/target/release/app.exe Kalima.exe
```

The desktop app automatically:
- Starts the Rust API server in-process
- Opens in a native window (no external browser)
- Loads data from `kalima.db` and `kalima-index/` in the project directory

### CLI/Server Mode
```bash
# Clone repository
git clone https://github.com/wwwportal/Kalima.git
cd Kalima

# Build and copy executable to root
cd engine
cargo build --release --bin kalima-api
cp target/release/kalima-api.exe ../kalima.exe
cd ..

# Ingest data (first time only)
./kalima.exe --help  # (or use: cargo run --bin kalima-ingest from engine/)

# Start server from project root (serves http://localhost:8080)
./kalima.exe
```

## Architecture

- **Backend:** Rust (Axum + SQLite + Tantivy)
  - 2,900 lines across 4 crates
  - 50+ REST endpoints
  - <1s startup, ~50MB memory
- **Frontend:** Vanilla JavaScript
  - 17 modular files, no build system
  - Layered canvas architecture

## Features

- Browse 114 surahs, 6,236 verses
- Full-text search with Arabic diacritics
- Root-based morphological search
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
cd engine
cargo test
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
