# ---------------------------------------------------------------------------
# Platform Runner — minimal platform service image
#
# This image packages the runner service Python code for the platform.
# It is NOT an agent runtime image — it does not execute agents.
# It is NOT a production network service — no ports are exposed.
#
# Security principles:
#   - non-root user (runner:runner, UID/GID 10002)
#   - no docker.sock
#   - no host secrets
#   - no registry credentials baked in
#   - no Git credentials, SSH keys, or credential helpers
#   - no Docker CLI
#   - no privileged mode
#   - no automatic apply-patch to canonical repository
# ---------------------------------------------------------------------------

FROM python:3.12-slim AS base

LABEL org.opencontainers.image.title="Platform Runner"
LABEL org.opencontainers.image.description="Platform runner service image for the Ariadne engineering platform — packages the runner service with Python 3.12 and a non-root user."
LABEL org.opencontainers.image.source="https://github.com/<org>/<repo>"
LABEL org.opencontainers.image.version="0.1.0"
LABEL org.opencontainers.image.revision="<placeholder>"
LABEL org.opencontainers.image.licenses="MIT"

# ---------------------------------------------------------------------------
# Install minimal OS packages (ca-certificates for TLS connectivity)
# ---------------------------------------------------------------------------
RUN apt-get update -qq \
    && apt-get install -y -qq --no-install-recommends \
        ca-certificates \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# ---------------------------------------------------------------------------
# Create non-root user and runtime directories
# ---------------------------------------------------------------------------
RUN groupadd --gid 10002 runner \
    && useradd --uid 10002 --gid runner --shell /bin/bash --create-home runner \
    && mkdir -p /app /tmp/platform-runner \
    && chown -R runner:runner /app /tmp/platform-runner

WORKDIR /app

# ---------------------------------------------------------------------------
# Copy runner service source code
# ---------------------------------------------------------------------------
COPY services/runner/src/runner /app/services/runner/src/runner

# ---------------------------------------------------------------------------
# Set Python path so imports like services.runner.src.runner.models resolve
# ---------------------------------------------------------------------------
ENV PYTHONPATH=/app

# ---------------------------------------------------------------------------
# Drop privileges
# ---------------------------------------------------------------------------
USER runner

# ---------------------------------------------------------------------------
# Default command: validate that the runner package is importable
# ---------------------------------------------------------------------------
CMD ["python", "-c", "import runner; print('runner image ready')"]
