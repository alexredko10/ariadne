# ---------------------------------------------------------------------------
# Agent Runtime Python — minimal controlled agent runtime
#
# This image is a generic Python base for controlled Docker Agents.
# It is NOT a platform service image — it does not run the runner,
# conductor, core, model gateway, or task intake.
#
# Security principles:
#   - non-root user (agent:agent, UID/GID 10001)
#   - no docker.sock
#   - no host secrets
#   - no registry credentials baked in
#   - no repository source copied into the image
#   - no Git credentials, SSH keys, or credential helpers
#   - no Docker CLI
# ---------------------------------------------------------------------------

FROM python:3.12-slim AS base

LABEL org.opencontainers.image.title="Agent Runtime Python"
LABEL org.opencontainers.image.description="Minimal Python base image for controlled Docker Agents — includes Python 3.12, pip, git, ca-certificates, and a non-root user."
LABEL org.opencontainers.image.source="https://github.com/<org>/<repo>"
LABEL org.opencontainers.image.version="0.1.0"
LABEL org.opencontainers.image.revision="<placeholder>"
LABEL org.opencontainers.image.licenses="MIT"

# ---------------------------------------------------------------------------
# Install minimal OS packages
# ---------------------------------------------------------------------------
RUN apt-get update -qq \
    && apt-get install -y -qq --no-install-recommends \
        git \
        ca-certificates \
        bash \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# ---------------------------------------------------------------------------
# Create non-root user and workspace
# ---------------------------------------------------------------------------
RUN groupadd --gid 10001 agent \
    && useradd --uid 10001 --gid agent --shell /bin/bash --create-home agent \
    && mkdir -p /workspace \
    && chown -R agent:agent /workspace

WORKDIR /workspace
USER agent

# ---------------------------------------------------------------------------
# Smoke test — verify key tools are present
# ---------------------------------------------------------------------------
RUN python --version \
    && pip --version \
    && git --version \
    && echo "agent-runtime-python base image built successfully"
