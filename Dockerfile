FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends git && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv

COPY pyproject.toml .
RUN uv pip install --system -e .

COPY src/ ./src/

ENV PYTHONPATH=/app

ENV MCP_TRANSPORT=http
ENV MCP_PORT=8765
EXPOSE 8765
CMD ["python", "-m", "src.server"]