# Kalima - Quranic Research Platform

High-performance web application for Quranic text analysis, morphological research, and linguistic exploration.

## Quick Start

### Prerequisites
- Rust 1.70+ ([Install Rust](https://rustup.rs/))

### Build and Run
```bash
# Clone repository
git clone https://github.com/wwwportal/Kalima.git
cd Kalima

# Build
cd engine
cargo build --release

# Ingest data (first time only)
cargo run --bin kalima-ingest -- ../datasets/corpus/quran.jsonl

# Start server
cargo run --release --bin kalima-api
```

Open browser: **http://localhost:8080**

## Architecture

- **Backend:** Rust (Axum + SQLite + Tantivy)
  - 2,900 lines across 4 crates
  - 50+ REST endpoints
  - <1s startup, ~50MB memory
- **Frontend:** Vanilla JavaScript
  - 17 modular files, no build system
  - Layered canvas architecture

## Features

- ✅ Browse 114 surahs, 6,236 verses
- ✅ Full-text search with Arabic diacritics
- ✅ Root-based morphological search
- ✅ POS pattern search
- ✅ Verb form analysis (Forms I-X)
- ✅ Dependency tree visualization
- ✅ Annotations & connections
- ✅ Hypothesis management
- ✅ Translation comparison

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
