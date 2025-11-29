# Build stage
FROM rust:1.75 as builder
WORKDIR /app
COPY engine/ ./engine/
WORKDIR /app/engine
RUN cargo build --release --bin kalima-api

# Runtime stage
FROM debian:bookworm-slim
WORKDIR /app

# Install SQLite
RUN apt-get update && apt-get install -y sqlite3 && rm -rf /var/lib/apt/lists/*

# Copy binary and assets
COPY --from=builder /app/engine/target/release/kalima-api /app/
COPY kalima.db /app/
COPY kalima-index/ /app/kalima-index/
COPY static/ /app/static/
COPY datasets/ /app/datasets/

ENV RUST_LOG=info
ENV KALIMA_DB=/app/kalima.db
ENV KALIMA_INDEX=/app/kalima-index

EXPOSE 8080
CMD ["/app/kalima-api"]
