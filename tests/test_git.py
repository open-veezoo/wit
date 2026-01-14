"""Tests for git module."""

import subprocess
import tempfile
from pathlib import Path

import pytest

from wit.git import (
    has_changes,
    get_changed_files,
    get_added_or_modified_files,
    stage_files,
    commit_changes,
    is_git_repo,
    get_repo_root,
    GitError,
)


@pytest.fixture
def git_repo(tmp_path):
    """Create a temporary git repository."""
    # Initialize git repo
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=tmp_path, check=True, capture_output=True
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=tmp_path, check=True, capture_output=True
    )
    
    # Create initial commit
    (tmp_path / "README.md").write_text("# Test")
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Initial commit"],
        cwd=tmp_path, check=True, capture_output=True
    )
    
    # Change to the repo directory
    import os
    original_dir = os.getcwd()
    os.chdir(tmp_path)
    
    yield tmp_path
    
    # Restore original directory
    os.chdir(original_dir)


class TestHasChanges:
    """Tests for has_changes function."""
    
    def test_no_changes(self, git_repo):
        """Test when there are no changes."""
        assert has_changes() is False
    
    def test_with_new_file(self, git_repo):
        """Test with a new file."""
        (git_repo / "new_file.txt").write_text("content")
        assert has_changes() is True
    
    def test_with_modified_file(self, git_repo):
        """Test with a modified file."""
        (git_repo / "README.md").write_text("# Modified")
        assert has_changes() is True


class TestGetChangedFiles:
    """Tests for get_changed_files function."""
    
    def test_no_changes(self, git_repo):
        """Test when there are no changes."""
        assert get_changed_files() == []
    
    def test_new_file(self, git_repo):
        """Test with a new file."""
        (git_repo / "new_file.txt").write_text("content")
        files = get_changed_files()
        assert "new_file.txt" in files
    
    def test_modified_file(self, git_repo):
        """Test with a modified file."""
        (git_repo / "README.md").write_text("# Modified")
        files = get_changed_files()
        assert "README.md" in files
    
    def test_multiple_files(self, git_repo):
        """Test with multiple changed files."""
        (git_repo / "file1.txt").write_text("content1")
        (git_repo / "file2.txt").write_text("content2")
        files = get_changed_files()
        assert len(files) == 2


class TestGetAddedOrModifiedFiles:
    """Tests for get_added_or_modified_files function."""
    
    def test_excludes_deleted(self, git_repo):
        """Test that deleted files are excluded."""
        # Create and commit a file
        (git_repo / "to_delete.txt").write_text("content")
        subprocess.run(["git", "add", "."], cwd=git_repo, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Add file"],
            cwd=git_repo, check=True, capture_output=True
        )
        
        # Delete the file
        (git_repo / "to_delete.txt").unlink()
        
        # Add a new file too
        (git_repo / "new_file.txt").write_text("new")
        
        files = get_added_or_modified_files()
        assert "new_file.txt" in files
        assert "to_delete.txt" not in files


class TestStageFiles:
    """Tests for stage_files function."""
    
    def test_stage_all(self, git_repo):
        """Test staging all files."""
        (git_repo / "file1.txt").write_text("content1")
        (git_repo / "file2.txt").write_text("content2")
        
        stage_files()
        
        # Check staged files
        result = subprocess.run(
            ["git", "diff", "--cached", "--name-only"],
            cwd=git_repo, capture_output=True, text=True
        )
        assert "file1.txt" in result.stdout
        assert "file2.txt" in result.stdout
    
    def test_stage_specific_files(self, git_repo):
        """Test staging specific files."""
        (git_repo / "file1.txt").write_text("content1")
        (git_repo / "file2.txt").write_text("content2")
        
        stage_files(["file1.txt"])
        
        result = subprocess.run(
            ["git", "diff", "--cached", "--name-only"],
            cwd=git_repo, capture_output=True, text=True
        )
        assert "file1.txt" in result.stdout
        assert "file2.txt" not in result.stdout


class TestCommitChanges:
    """Tests for commit_changes function."""
    
    def test_commit_with_changes(self, git_repo):
        """Test committing with changes."""
        (git_repo / "new_file.txt").write_text("content")
        
        sha = commit_changes("Test commit", "Test Bot", "test@bot.com")
        
        assert sha is not None
        
        # Verify commit
        result = subprocess.run(
            ["git", "log", "-1", "--pretty=format:%s"],
            cwd=git_repo, capture_output=True, text=True
        )
        assert result.stdout == "Test commit"
    
    def test_commit_no_changes(self, git_repo):
        """Test committing with no changes."""
        sha = commit_changes("Test commit", "Test Bot", "test@bot.com")
        assert sha is None
    
    def test_commit_author(self, git_repo):
        """Test commit author is set correctly."""
        (git_repo / "new_file.txt").write_text("content")
        
        commit_changes("Test commit", "Custom Bot", "custom@bot.com")
        
        result = subprocess.run(
            ["git", "log", "-1", "--pretty=format:%an <%ae>"],
            cwd=git_repo, capture_output=True, text=True
        )
        assert result.stdout == "Custom Bot <custom@bot.com>"


class TestIsGitRepo:
    """Tests for is_git_repo function."""
    
    def test_in_git_repo(self, git_repo):
        """Test inside a git repo."""
        assert is_git_repo() is True
    
    def test_not_in_git_repo(self, tmp_path):
        """Test outside a git repo."""
        import os
        original_dir = os.getcwd()
        os.chdir(tmp_path)
        
        try:
            assert is_git_repo() is False
        finally:
            os.chdir(original_dir)


class TestGetRepoRoot:
    """Tests for get_repo_root function."""
    
    def test_get_root(self, git_repo):
        """Test getting repo root."""
        root = get_repo_root()
        assert root == git_repo
    
    def test_from_subdirectory(self, git_repo):
        """Test getting repo root from subdirectory."""
        import os
        
        subdir = git_repo / "subdir"
        subdir.mkdir()
        os.chdir(subdir)
        
        root = get_repo_root()
        assert root == git_repo
