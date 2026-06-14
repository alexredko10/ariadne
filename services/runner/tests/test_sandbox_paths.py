"""Tests for sandbox path isolation.

Sandbox paths must be isolated from the canonical repository.  The path
validator must reject host-sensitive paths to prevent accidental or
malicious access to host resources.
"""

import pytest

from services.runner.src.runner.patch import normalize_repo_path


class TestSandboxPathIsolation:
    """Documents the sandbox isolation invariant."""

    def test_docker_socket_rejected(self):
        """The Docker daemon socket path must be rejected.

        Rationale: a sandbox must not be able to communicate with the host
        Docker daemon unless explicitly approved.
        """
        with pytest.raises(ValueError):
            normalize_repo_path("/var/run/docker.sock")

    def test_etc_passwd_rejected(self):
        """Absolute paths referencing system files are rejected."""
        with pytest.raises(ValueError):
            normalize_repo_path("/etc/passwd")

    def test_boot_volume_rejected(self):
        """Root-level host paths are not repo-relative and must be rejected."""
        with pytest.raises(ValueError):
            normalize_repo_path("/")

    def test_home_directory_rejected(self):
        """User home is outside the canonical repository."""
        with pytest.raises(ValueError):
            normalize_repo_path("/home/user/file.py")

    def test_tmp_dir_rejected(self):
        """Temporary directories on the host are outside the repository."""
        with pytest.raises(ValueError):
            normalize_repo_path("/tmp/sandbox_escape")

    def test_proc_filesystem_rejected(self):
        """Process filesystem is host-internal."""
        with pytest.raises(ValueError):
            normalize_repo_path("/proc/self/environ")

    def test_dev_paths_rejected(self):
        """Device files are host-specific."""
        with pytest.raises(ValueError):
            normalize_repo_path("/dev/sda1")
