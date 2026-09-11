FROM debian:bookworm-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends git ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && git config --system core.hooksPath /dev/null

WORKDIR /workspace
# Analysis is static-only; cloned code is never executed.
