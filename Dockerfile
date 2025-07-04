# syntax=docker/dockerfile:1
FROM python:3.11-slim as base

# System deps and uv for fast Python installs
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    && pip install --no-cache-dir uv \
    && apt-get purge -y --auto-remove build-essential \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m odinuser
WORKDIR /app

# Only copy files needed for dependency install first (for Docker cache efficiency)
COPY pyproject.toml uv.lock README.md odinbot/ ./

# Install dependencies (including test dependencies for pytest) in editable mode
RUN uv pip install --system --no-cache-dir -e '.[test]'

# Now copy the rest of the code
COPY tests/ ./tests/

# Create logs directory and set permissions
RUN mkdir -p logs && chown -R odinuser:odinuser logs

# Switch to non-root user
USER odinuser

# Environment variables GUILD_ID and CHANNEL_ID must be set for the bot to start correctly
CMD ["odinbot", "agent", "--guild-id", "${GUILD_ID}", "--channel-id", "${CHANNEL_ID}"] 