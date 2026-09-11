"""Sandbox resource limits for repo ingestion.

v1 isolation is a locked-down shallow clone (git hooks disabled, no
execution of cloned code). These caps apply whether the clone runs on the
host or in the sandbox image under infra/docker/sandbox.Dockerfile.
"""

MAX_REPO_BYTES = 80 * 1024 * 1024
CLONE_TIMEOUT_SECONDS = 90
MAX_FILES = 2000
MAX_FILE_BYTES = 256_000
