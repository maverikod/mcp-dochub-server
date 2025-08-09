"""Git status command using GitPython."""

import os
from typing import Dict, Any, Optional, List
from mcp_proxy_adapter.commands.base import Command
from mcp_proxy_adapter.commands.result import SuccessResult, ErrorResult

try:
    from git import Repo, InvalidGitRepositoryError
except ImportError:
    Repo = None
    InvalidGitRepositoryError = Exception


class GitStatusCommand(Command):
    """Get Git repository status using GitPython."""
    
    name = "git_status"
    
    async def execute(
        self,
        repository_path: Optional[str] = None,
        **kwargs
    ) -> SuccessResult:
        """Get Git repository status.
        
        Args:
            repository_path: Path to Git repository (defaults to current directory)
            
        Returns:
            SuccessResult with repository status information
        """
        try:
            if Repo is None:
                return ErrorResult(
                    message="GitPython library is not installed. Install with: pip install GitPython",
                    code="MISSING_DEPENDENCY",
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
            
            # Get repository information
            repo_info = {
                "repository_path": os.path.abspath(repo.working_dir),
                "git_directory": repo.git_dir,
                "is_bare": repo.bare,
                "current_branch": None,
                "active_branch": None,
                "head_commit": None,
                "is_dirty": repo.is_dirty(),
                "untracked_files": [],
                "modified_files": [],
                "staged_files": [],
                "deleted_files": [],
                "renamed_files": [],
                "remote_branches": [],
                "local_branches": [],
                "tags": []
            }
            
            # Get current branch info
            try:
                if not repo.bare and repo.head.is_valid():
                    repo_info["current_branch"] = repo.active_branch.name
                    repo_info["active_branch"] = str(repo.active_branch)
                    repo_info["head_commit"] = {
                        "sha": repo.head.commit.hexsha,
                        "short_sha": repo.head.commit.hexsha[:7],
                        "message": repo.head.commit.message.strip(),
                        "author": str(repo.head.commit.author),
                        "committed_date": repo.head.commit.committed_date
                    }
            except Exception:
                # Handle detached HEAD or other edge cases
                try:
                    if repo.head.is_valid():
                        repo_info["head_commit"] = {
                            "sha": repo.head.commit.hexsha,
                            "short_sha": repo.head.commit.hexsha[:7],
                            "message": repo.head.commit.message.strip(),
                            "author": str(repo.head.commit.author),
                            "committed_date": repo.head.commit.committed_date
                        }
                        repo_info["current_branch"] = "HEAD (detached)"
                except Exception:
                    pass
            
            # Get file status
            if not repo.bare:
                # Untracked files
                repo_info["untracked_files"] = repo.untracked_files
                
                # Modified files (working directory changes)
                repo_info["modified_files"] = [item.a_path for item in repo.index.diff(None)]
                
                # Staged files (index changes)
                repo_info["staged_files"] = [item.a_path for item in repo.index.diff("HEAD")]
                
                # Get more detailed diff info
                try:
                    diff_info = []
                    for diff in repo.index.diff(None):
                        diff_info.append({
                            "file": diff.a_path,
                            "change_type": diff.change_type,
                            "deleted": diff.deleted_file,
                            "new": diff.new_file,
                            "renamed": diff.renamed_file
                        })
                    repo_info["file_changes"] = diff_info
                except Exception:
                    pass
            
            # Get branches
            try:
                repo_info["local_branches"] = [branch.name for branch in repo.branches]
                repo_info["remote_branches"] = [branch.name for branch in repo.remotes.origin.refs] if repo.remotes else []
            except Exception:
                pass
            
            # Get tags
            try:
                repo_info["tags"] = [tag.name for tag in repo.tags]
            except Exception:
                pass
            
            # Get remotes
            try:
                remotes = {}
                for remote in repo.remotes:
                    remotes[remote.name] = {
                        "url": list(remote.urls)[0] if remote.urls else None,
                        "fetch_url": remote.url,
                        "push_url": getattr(remote, 'pushurl', remote.url)
                    }
                repo_info["remotes"] = remotes
            except Exception:
                repo_info["remotes"] = {}
            
            # Calculate summary
            summary = {
                "clean": not repo.is_dirty() and not repo.untracked_files,
                "total_files_changed": len(repo_info["modified_files"]) + len(repo_info["staged_files"]) + len(repo_info["untracked_files"]),
                "has_uncommitted_changes": repo.is_dirty(),
                "has_untracked_files": bool(repo.untracked_files),
                "branch_status": "clean" if not repo.is_dirty() and not repo.untracked_files else "dirty"
            }
            
            # Success response
            return SuccessResult(data={
                "status": "success",
                "message": f"Git status for repository '{repo_info['repository_path']}'",
                "repository": repo_info,
                "summary": summary
            })
            
        except Exception as e:
            return ErrorResult(
                message=f"Unexpected error getting Git status: {str(e)}",
                code="UNEXPECTED_ERROR",
                details={"error_type": type(e).__name__}
            )
    
    @classmethod
    def get_schema(cls) -> Dict[str, Any]:
        """Get the JSON schema for this command."""
        return {
            "type": "object",
            "properties": {
                "repository_path": {
                    "type": "string",
                    "description": "Path to Git repository (optional, defaults to current directory)"
                }
            },
            "required": [],
            "additionalProperties": False
        } 