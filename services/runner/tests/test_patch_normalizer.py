"""Tests for patch path normalization and forbidden-path rejection."""

import pytest

from services.runner.src.runner.patch import (
    is_forbidden_patch_path,
    normalize_patch_text,
    normalize_repo_path,
    validate_patch_path,
)


# ---------------------------------------------------------------------------
# normalize_repo_path – structural validity
# ---------------------------------------------------------------------------


class TestNormalizeRepoPath:
    def test_accepts_normal_repo_relative_path(self):
        assert normalize_repo_path("src/module.py") == "src/module.py"

    def test_repeated_slashes_normalized(self):
        assert normalize_repo_path("src//module.py") == "src/module.py"

    def test_rejects_absolute_posix_path(self):
        with pytest.raises(ValueError, match="absolute"):
            normalize_repo_path("/etc/passwd")

    def test_rejects_windows_backslash_path(self):
        with pytest.raises(ValueError, match="drive-letter"):
            normalize_repo_path(r"C:\etc\passwd")

    def test_rejects_windows_forward_slash_path(self):
        with pytest.raises(ValueError, match="drive-letter"):
            normalize_repo_path("C:/etc/passwd")

    def test_rejects_windows_drive_relative_path(self):
        with pytest.raises(ValueError, match="drive-letter"):
            normalize_repo_path("C:relative/path")

    def test_rejects_double_dot_traversal(self):
        with pytest.raises(ValueError, match="directory traversal"):
            normalize_repo_path("../etc/passwd")

    def test_rejects_empty_string(self):
        with pytest.raises(ValueError, match="empty"):
            normalize_repo_path("")

    def test_rejects_whitespace_only(self):
        with pytest.raises(ValueError, match="whitespace-only"):
            normalize_repo_path("   ")

    def test_rejects_leading_whitespace(self):
        with pytest.raises(ValueError, match="leading or trailing whitespace"):
            normalize_repo_path(" file.py")

    def test_rejects_trailing_whitespace(self):
        with pytest.raises(ValueError, match="leading or trailing whitespace"):
            normalize_repo_path("file.py ")

    def test_rejects_nul_byte(self):
        with pytest.raises(ValueError, match="NUL byte"):
            normalize_repo_path("fi\0le.py")

    def test_rejects_control_characters(self):
        with pytest.raises(ValueError, match="control character"):
            normalize_repo_path("file\x01.py")

    def test_rejects_current_dir_dot(self):
        with pytest.raises(ValueError, match="current-directory"):
            normalize_repo_path(".")

    def test_rejects_path_that_normalizes_to_dot(self):
        with pytest.raises(ValueError, match="current-directory"):
            normalize_repo_path("./")

    def test_accepts_deep_repo_relative(self):
        assert normalize_repo_path("a/b/c/d.py") == "a/b/c/d.py"

    def test_rejects_non_string_input(self):
        with pytest.raises(TypeError):
            normalize_repo_path(None)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# is_forbidden_patch_path – forbidden location checks
# ---------------------------------------------------------------------------


class TestIsForbiddenPatchPath:
    def test_git_config_rejected(self):
        assert is_forbidden_patch_path(".git/config") is True

    def test_git_directory_rejected(self):
        assert is_forbidden_patch_path(".git") is True

    def test_git_subpath_rejected(self):
        assert is_forbidden_patch_path(".git/HEAD") is True

    def test_project_memory_contracts_rejected(self):
        assert is_forbidden_patch_path(".project-memory/project_contract.yml") is True

    def test_project_memory_other_pr_rejected(self):
        assert is_forbidden_patch_path(".project-memory/pr/other/PLAN.md") is True

    def test_project_memory_other_file_rejected(self):
        assert (
            is_forbidden_patch_path(
                ".project-memory/pr/0001-runner-patch-contracts/OTHER.md"
            )
            is True
        )

    def test_project_memory_whitelist_accepted(self):
        assert (
            is_forbidden_patch_path(
                ".project-memory/pr/0001-runner-patch-contracts/PLAN.md"
            )
            is False
        )

    def test_dot_env_rejected(self):
        assert is_forbidden_patch_path(".env") is True

    def test_dot_env_prod_rejected(self):
        assert is_forbidden_patch_path(".env.prod") is True

    def test_dot_env_local_rejected(self):
        assert is_forbidden_patch_path(".env.local") is True

    def test_private_key_uppercase_rejected(self):
        assert is_forbidden_patch_path("PRIVATE.KEY") is True

    def test_cert_pem_case_insensitive_rejected(self):
        assert is_forbidden_patch_path("cert.PEM") is True

    def test_secret_in_basename_rejected(self):
        assert is_forbidden_patch_path("mySecret.txt") is True

    def test_token_in_basename_rejected(self):
        assert is_forbidden_patch_path("api_TOKEN.json") is True

    def test_credential_in_basename_rejected(self):
        assert is_forbidden_patch_path("dbCredential.yml") is True

    def test_id_rsa_rejected(self):
        assert is_forbidden_patch_path("id_rsa") is True

    def test_id_ed25519_rejected(self):
        assert is_forbidden_patch_path("id_ed25519") is True

    def test_safe_path_not_forbidden(self):
        assert is_forbidden_patch_path("src/app.py") is False

    def test_hidden_file_not_forbidden(self):
        assert is_forbidden_patch_path(".gitignore") is False


# ---------------------------------------------------------------------------
# validate_patch_path – combined normalisation + forbidden check
# ---------------------------------------------------------------------------


class TestValidatePatchPath:
    def test_accepts_valid_repo_path(self):
        assert validate_patch_path("src/main.py") == "src/main.py"

    def test_rejects_git_path(self):
        with pytest.raises(ValueError, match="forbidden"):
            validate_patch_path(".git/config")

    def test_rejects_project_memory_path(self):
        with pytest.raises(ValueError, match="forbidden"):
            validate_patch_path(".project-memory/anchors.yml")


# ---------------------------------------------------------------------------
# normalize_patch_text – unified diff parsing
# ---------------------------------------------------------------------------


class TestNormalizePatchText:
    def test_empty_diff_returns_empty_patch(self):
        patch = normalize_patch_text("")
        assert patch.text == ""
        assert patch.touched_paths == ()

    def test_whitespace_only_diff_returns_empty_patch(self):
        patch = normalize_patch_text("   \n  \n")
        assert patch.touched_paths == ()

    def test_extracts_plus_plus_paths(self):
        diff = "+++ b/src/main.py\n"
        patch = normalize_patch_text(diff)
        assert patch.touched_paths == ("src/main.py",)

    def test_extracts_minus_minus_paths(self):
        diff = "--- a/src/main.py\n"
        patch = normalize_patch_text(diff)
        assert patch.touched_paths == ("src/main.py",)

    def test_extracts_diff_git_paths(self):
        diff = "diff --git a/src/main.py b/src/main.py\n"
        patch = normalize_patch_text(diff)
        assert patch.touched_paths == ("src/main.py",)

    def test_deduplicates_duplicate_paths(self):
        diff = (
            "diff --git a/src/main.py b/src/main.py\n"
            "--- a/src/main.py\n"
            "+++ b/src/main.py\n"
        )
        patch = normalize_patch_text(diff)
        assert patch.touched_paths == ("src/main.py",)

    def test_multiple_files_extracted(self):
        diff = (
            "diff --git a/a.py b/a.py\n"
            "--- a/a.py\n"
            "+++ b/a.py\n"
            "diff --git a/b.py b/b.py\n"
            "--- a/b.py\n"
            "+++ b/b.py\n"
        )
        patch = normalize_patch_text(diff)
        assert len(patch.touched_paths) == 2
        assert "a.py" in patch.touched_paths
        assert "b.py" in patch.touched_paths

    def test_rejects_forbidden_patch_target(self):
        diff = "+++ b/.git/config\n"
        with pytest.raises(ValueError, match="forbidden"):
            normalize_patch_text(diff)

    def test_preserves_diff_text(self):
        diff = "+++ b/file.py\n@@ -1 +1 @@\n-old\n+new\n"
        patch = normalize_patch_text(diff)
        assert patch.text == diff
