"""Git commit command using GitPython."""

import os
from typing import Dict, Any, Optional, List
from mcp_proxy_adapter.commands.base import Command
from mcp_proxy_adapter.commands.result import SuccessResult, ErrorResult

try:
    from git import Repo, InvalidGitRepositoryError
except ImportError:
    Repo = None
    InvalidGitRepositoryError = Exception


class GitCommitCommand(Command):
    """Create Git commit using GitPython."""
    
    name = "git_commit"
    
    async def execute(
        self,
        message: str,
        repository_path: Optional[str] = None,
        add_all: bool = False,
        files: Optional[List[str]] = None,
        author_name: Optional[str] = None,
        author_email: Optional[str] = None,
        **kwargs
    ) -> SuccessResult:
        """Create a Git commit.
        
        Args:
            message: Commit message
            repository_path: Path to Git repository (defaults to current directory)
            add_all: Add all modified files before commit
            files: Specific files to add before commit
            author_name: Override author name
            author_email: Override author email
            
        Returns:
            SuccessResult with commit information
        """
        try:
            if Repo is None:
                return ErrorResult(
                    message="GitPython library is not installed. Install with: pip install GitPython",
                    code="MISSING_DEPENDENCY",
                    details={}
                )
            
            if not message or not message.strip():
                return ErrorResult(
                    message="Commit message is required",
                    code="MISSING_MESSAGE",
                    details={}
                )
            
            # Set working directory
            repo_path = repository_path if repository_path else os.getcwd()
            
            # Check if directory exists
            if not os.path.exists(repo_path):
                return ErrorResult(
                    message=f"Directory '{repo_path}' does not exist",
                    code="DIRECTORY_NOT_FOUND",
                    details={"directory": repo_path}
                )
            
            # Open repository
            try:
                repo = Repo(repo_path)
            except InvalidGitRepositoryError:
                return ErrorResult(
                    message=f"'{repo_path}' is not a Git repository",
                    code="NOT_GIT_REPOSITORY",
                    details={"directory": repo_path}
                )
            
            if repo.bare:
                return ErrorResult(
                    message="Cannot commit to a bare repository",
                    code="BARE_REPOSITORY",
                    details={}
                )
            
            # Add files if requested
            added_files = []
            if add_all:
                # Add all modified and untracked files
                repo.git.add(A=True)
                added_files.append("all files (git add -A)")
            elif files:
                # Add specific files
                for file_path in files:
                    if os.path.exists(os.path.join(repo.working_dir, file_path)):
                        repo.index.add([file_path])
                        added_files.append(file_path)
                    else:
                        return ErrorResult(
                            message=f"File '{file_path}' not found",
                            code="FILE_NOT_FOUND",
                            details={"file": file_path}
                        )
            
            # Check if there are staged changes
            if not repo.index.diff("HEAD"):
                return ErrorResult(
                    message="No changes staged for commit",
                    code="NOTHING_TO_COMMIT",
                    details={
                        "suggestion": "Use add_all=true or specify files to add changes"
                    }
                )
            
            # Set author if provided
            author = None
            if author_name or author_email:
                from git import Actor
                author = Actor(
                    name=author_name or repo.config_reader().get_value("user", "name", fallback="Unknown"),
                    email=author_email or repo.config_reader().get_value("user", "email", fallback="unknown@example.com")
                )
            
            # Create commit
            try:
                commit = repo.index.commit(
                    message=message.strip(),
                    author=author,
                    committer=author
                )
            except Exception as e:
                return ErrorResult(
                    message=f"Failed to create commit: {str(e)}",
                    code="COMMIT_FAILED",
                    details={"error": str(e)}
                )
            
            # Get commit information
            commit_info = {
                "sha": commit.hexsha,
                "short_sha": commit.hexsha[:7],
                "message": commit.message.strip(),
                "author": {
                    "name": commit.author.name,
                    "email": commit.author.email
                },
                "committer": {
                    "name": commit.committer.name,
                    "email": commit.committer.email
                },
                "committed_date": commit.committed_date,
                "authored_date": commit.authored_date,
                "stats": {
                    "files_changed": len(commit.stats.files),
                    "insertions": commit.stats.total["insertions"],
                    "deletions": commit.stats.total["deletions"],
                    "lines_changed": commit.stats.total["lines"]
                }
            }
            
            # Get current branch info
            branch_info = {}
            try:
                if repo.head.is_valid():
                    branch_info = {
                        "current_branch": repo.active_branch.name if not repo.head.is_detached else "HEAD (detached)",
                        "head_commit": commit.hexsha
                    }
            except Exception:
                pass
            
            # Success response
            return SuccessResult(data={
                "status": "success",
                "message": f"Commit created successfully: {commit.hexsha[:7]}",
                "commit": commit_info,
                "branch": branch_info,
                "repository_path": os.path.abspath(repo.working_dir),
                "added_files": added_files,
                "options": {
                    "add_all": add_all,
                    "files": files,
                    "author_override": bool(author_name or author_email)
                }
            })
            
        except Exception as e:
            return ErrorResult(
                message=f"Unexpected error creating commit: {str(e)}",
                code="UNEXPECTED_ERROR",
                details={"error_type": type(e).__name__}
            )
    
    @classmethod
    def get_schema(cls) -> Dict[str, Any]:
        """Get the JSON schema for this command."""
        return {
            "type": "object",
            "properties": {
                "message": {
                    "type": "string",
                    "description": "Commit message (required)"
                },
                "repository_path": {
                    "type": "string",
                    "description": "Path to Git repository (optional, defaults to current directory)"
                },
                "add_all": {
                    "type": "boolean",
                    "description": "Add all modified files before commit",
                    "default": False
                },
                "files": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Specific files to add before commit"
                },
                "author_name": {
                    "type": "string",
                    "description": "Override author name for this commit"
                },
                "author_email": {
                    "type": "string",
                    "description": "Override author email for this commit"
                }
            },
            "required": ["message"],
            "additionalProperties": False
        } 