"""Git operations for wit."""

import subprocess
from pathlib import Path

from wit.utils import get_logger


class GitError(Exception):
    """Exception raised during git operations."""
    pass


def has_changes() -> bool:
    """Check if there are uncommitted changes.
    
    Returns:
        True if there are changes to commit.
    """
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True,
            text=True,
            check=True,
        )
        return bool(result.stdout.strip())
    except subprocess.CalledProcessError as e:
        raise GitError(f"Failed to check git status: {e.stderr}")


def get_changed_files() -> list[str]:
    """Get list of changed files (staged and unstaged).
    
    Returns:
        List of changed file paths.
    """
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True,
            text=True,
            check=True,
        )
        
        files = []
        # Use rstrip() to preserve leading spaces which are part of the status format
        for line in result.stdout.rstrip().split("\n"):
            if line:
                # Format: XY filename or XY -> newfilename (for renames)
                # XY = 2 status chars, then space, then filename
                # Skip the status codes (first 3 chars: XY + space)
                filepath = line[3:].strip()
                
                # Handle renames
                if " -> " in filepath:
                    filepath = filepath.split(" -> ")[1]
                
                files.append(filepath)
        
        return files
        
    except subprocess.CalledProcessError as e:
        raise GitError(f"Failed to get changed files: {e.stderr}")


def get_added_or_modified_files() -> list[str]:
    """Get list of added or modified markdown files.
    
    Returns:
        List of added/modified file paths (excluding deletions).
    """
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True,
            text=True,
            check=True,
        )
        
        files = []
        # Use rstrip() to preserve leading spaces which are part of the status format
        for line in result.stdout.rstrip().split("\n"):
            if line:
                status = line[:2]
                filepath = line[3:].strip()
                
                # Skip deletions (D in either position)
                if "D" in status:
                    continue
                
                # Handle renames
                if " -> " in filepath:
                    filepath = filepath.split(" -> ")[1]
                
                files.append(filepath)
        
        return files
        
    except subprocess.CalledProcessError as e:
        raise GitError(f"Failed to get changed files: {e.stderr}")


def stage_files(files: list[str] | None = None) -> None:
    """Stage files for commit.
    
    Args:
        files: List of files to stage. If None, stages all changes.
    """
    try:
        if files:
            subprocess.run(
                ["git", "add"] + files,
                capture_output=True,
                text=True,
                check=True,
            )
        else:
            subprocess.run(
                ["git", "add", "-A"],
                capture_output=True,
                text=True,
                check=True,
            )
    except subprocess.CalledProcessError as e:
        raise GitError(f"Failed to stage files: {e.stderr}")


def commit_changes(
    message: str,
    author_name: str = "wit[bot]",
    author_email: str = "wit[bot]@users.noreply.github.com",
) -> str | None:
    """Commit all changes with the given message.
    
    Args:
        message: Commit message.
        author_name: Git author name.
        author_email: Git author email.
        
    Returns:
        Commit SHA if changes were committed, None if no changes.
    """
    logger = get_logger()
    
    # Check for changes first
    if not has_changes():
        logger.info("No changes to commit")
        return None
    
    # Stage all changes
    stage_files()
    
    try:
        # Set author for this commit
        env = {
            "GIT_AUTHOR_NAME": author_name,
            "GIT_AUTHOR_EMAIL": author_email,
            "GIT_COMMITTER_NAME": author_name,
            "GIT_COMMITTER_EMAIL": author_email,
        }
        
        # Create commit
        import os
        full_env = os.environ.copy()
        full_env.update(env)
        
        result = subprocess.run(
            ["git", "commit", "-m", message],
            capture_output=True,
            text=True,
            check=True,
            env=full_env,
        )
        
        # Get commit SHA
        sha_result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        )
        
        return sha_result.stdout.strip()
        
    except subprocess.CalledProcessError as e:
        raise GitError(f"Failed to commit changes: {e.stderr}")


def is_git_repo() -> bool:
    """Check if current directory is inside a git repository.
    
    Returns:
        True if inside a git repo.
    """
    try:
        subprocess.run(
            ["git", "rev-parse", "--git-dir"],
            capture_output=True,
            text=True,
            check=True,
        )
        return True
    except subprocess.CalledProcessError:
        return False


def get_repo_root() -> Path:
    """Get the root directory of the git repository.
    
    Returns:
        Path to repository root.
        
    Raises:
        GitError: If not in a git repository.
    """
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            check=True,
        )
        return Path(result.stdout.strip())
    except subprocess.CalledProcessError as e:
        raise GitError(f"Failed to get repo root: {e.stderr}")
