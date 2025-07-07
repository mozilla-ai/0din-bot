# syntax=docker/dockerfile:1

# ---- PRODUCTION STAGE ----
FROM python:3.11-slim as prod

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    && pip install --no-cache-dir uv \
    && apt-get purge -y --auto-remove build-essential \
    && rm -rf /var/lib/apt/lists/*

RUN useradd -m odinuser
WORKDIR /app
COPY pyproject.toml uv.lock README.md ./
COPY odinbot/ ./odinbot/
RUN chown -R odinuser:odinuser /app
RUN uv pip install --system --no-cache-dir .
RUN mkdir -p logs && chown -R odinuser:odinuser logs
USER odinuser

CMD ["odinbot", "agent", "--guild-id", "${GUILD_ID}", "--channel-id", "${CHANNEL_ID}"]

# ---- TEST STAGE ----
FROM python:3.11-slim as test

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    && pip install --no-cache-dir uv \
    && apt-get purge -y --auto-remove build-essential \
    && rm -rf /var/lib/apt/lists/*

RUN useradd -m odinuser
WORKDIR /app
COPY pyproject.toml uv.lock README.md ./
COPY odinbot/ ./odinbot/
RUN chown -R odinuser:odinuser /app
RUN uv pip install --system --no-cache-dir '.[test]'
RUN mkdir -p logs && chown -R odinuser:odinuser logs
USER odinuser 