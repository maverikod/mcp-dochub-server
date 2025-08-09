"""Git push command using GitPython."""

import os
from typing import Dict, Any, Optional
from mcp_proxy_adapter.commands.base import Command
from mcp_proxy_adapter.commands.result import SuccessResult, ErrorResult

try:
    from git import Repo, InvalidGitRepositoryError, GitCommandError
except ImportError:
    Repo = None
    InvalidGitRepositoryError = Exception
    GitCommandError = Exception


class GitPushCommand(Command):
    """Push Git changes to remote repository using GitPython."""
    
    name = "git_push"
    
    async def execute(
        self,
        repository_path: Optional[str] = None,
        remote: str = "origin",
        branch: Optional[str] = None,
        force: bool = False,
        set_upstream: bool = False,
        **kwargs
    ) -> SuccessResult:
        """Push Git changes to remote repository.
        
        Args:
            repository_path: Path to Git repository (defaults to current directory)
            remote: Remote name to push to (default: origin)
            branch: Branch to push (defaults to current branch)
            force: Force push (use with caution)
            set_upstream: Set upstream tracking branch
            
        Returns:
            SuccessResult with push information
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
            
            if repo.bare:
                return ErrorResult(
                    message="Cannot push from a bare repository",
                    code="BARE_REPOSITORY",
                    details={}
                )
            
            # Get remote
            try:
                remote_obj = repo.remotes[remote]
            except IndexError:
                return ErrorResult(
                    message=f"Remote '{remote}' not found",
                    code="REMOTE_NOT_FOUND",
                    details={
                        "remote": remote,
                        "available_remotes": [r.name for r in repo.remotes]
                    }
                )
            
            # Determine branch to push
            push_branch = branch
            if not push_branch:
                try:
                    if repo.head.is_detached:
                        return ErrorResult(
                            message="HEAD is detached. Please specify a branch to push.",
                            code="DETACHED_HEAD",
                            details={}
                        )
                    push_branch = repo.active_branch.name
                except Exception:
                    return ErrorResult(
                        message="Could not determine current branch. Please specify a branch to push.",
                        code="UNKNOWN_BRANCH",
                        details={}
                    )
            
            # Check if branch exists
            try:
                local_branch = repo.branches[push_branch]
            except IndexError:
                return ErrorResult(
                    message=f"Branch '{push_branch}' not found",
                    code="BRANCH_NOT_FOUND",
                    details={
                        "branch": push_branch,
                        "available_branches": [b.name for b in repo.branches]
                    }
                )
            
            # Get pre-push information
            pre_push_info = {
                "repository_path": os.path.abspath(repo.working_dir),
                "remote": remote,
                "remote_url": remote_obj.url,
                "branch": push_branch,
                "local_commit": local_branch.commit.hexsha,
                "force": force,
                "set_upstream": set_upstream
            }
            
            # Check if there are changes to push
            try:
                # Get remote tracking branch
                tracking_branch = local_branch.tracking_branch()
                if tracking_branch:
                    commits_ahead = list(repo.iter_commits(f'{tracking_branch}..{local_branch}'))
                    commits_behind = list(repo.iter_commits(f'{local_branch}..{tracking_branch}'))
                    
                    pre_push_info["tracking_branch"] = tracking_branch.name
                    pre_push_info["commits_ahead"] = len(commits_ahead)
                    pre_push_info["commits_behind"] = len(commits_behind)
                    
                    if not commits_ahead:
                        return ErrorResult(
                            message="No changes to push. Local branch is up to date.",
                            code="UP_TO_DATE",
                            details=pre_push_info
                        )
                    
                    if commits_behind and not force:
                        return ErrorResult(
                            message=f"Local branch is {len(commits_behind)} commits behind remote. Use force=true to force push or pull first.",
                            code="BEHIND_REMOTE",
                            details=pre_push_info
                        )
                else:
                    pre_push_info["tracking_branch"] = None
                    pre_push_info["commits_ahead"] = "unknown"
                    pre_push_info["commits_behind"] = 0
                    
            except Exception as e:
                # If we can't determine the status, continue with the push
                pre_push_info["status_check_error"] = str(e)
            
            # Prepare push arguments
            push_args = [push_branch]
            push_kwargs = {}
            
            if force:
                push_kwargs['force'] = True
            
            if set_upstream:
                push_kwargs['set_upstream'] = True
            
            # Perform push
            try:
                push_info = remote_obj.push(*push_args, **push_kwargs)
            except GitCommandError as e:
                return ErrorResult(
                    message=f"Push failed: {str(e)}",
                    code="PUSH_FAILED",
                    details={
                        "error": str(e),
                        "pre_push_info": pre_push_info
                    }
                )
            except Exception as e:
                return ErrorResult(
                    message=f"Unexpected push error: {str(e)}",
                    code="PUSH_ERROR",
                    details={
                        "error": str(e),
                        "pre_push_info": pre_push_info
                    }
                )
            
            # Process push results
            push_results = []
            for push_result in push_info:
                result_info = {
                    "local_ref": str(push_result.local_ref),
                    "remote_ref": str(push_result.remote_ref) if push_result.remote_ref else None,
                    "flags": push_result.flags,
                    "summary": push_result.summary
                }
                
                # Check for errors
                if push_result.flags & push_result.ERROR:
                    result_info["error"] = "Push failed with error"
                elif push_result.flags & push_result.REJECTED:
                    result_info["error"] = "Push rejected"
                elif push_result.flags & push_result.UP_TO_DATE:
                    result_info["status"] = "up_to_date"
                elif push_result.flags & push_result.FAST_FORWARD:
                    result_info["status"] = "fast_forward"
                elif push_result.flags & push_result.FORCED_UPDATE:
                    result_info["status"] = "forced_update"
                else:
                    result_info["status"] = "success"
                
                push_results.append(result_info)
            
            # Check if any push failed
            failed_pushes = [r for r in push_results if "error" in r]
            if failed_pushes:
                return ErrorResult(
                    message="Some pushes failed",
                    code="PARTIAL_PUSH_FAILURE",
                    details={
                        "failed_pushes": failed_pushes,
                        "all_results": push_results,
                        "pre_push_info": pre_push_info
                    }
                )
            
            # Success response
            return SuccessResult(data={
                "status": "success",
                "message": f"Successfully pushed '{push_branch}' to '{remote}'",
                "push_results": push_results,
                "pre_push_info": pre_push_info,
                "summary": {
                    "pushed_branch": push_branch,
                    "remote": remote,
                    "forced": force,
                    "set_upstream": set_upstream,
                    "total_refs_pushed": len(push_results)
                }
            })
            
        except Exception as e:
            return ErrorResult(
                message=f"Unexpected error during push: {str(e)}",
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
                },
                "remote": {
                    "type": "string",
                    "description": "Remote name to push to",
                    "default": "origin"
                },
                "branch": {
                    "type": "string",
                    "description": "Branch to push (optional, defaults to current branch)"
                },
                "force": {
                    "type": "boolean",
                    "description": "Force push (use with caution)",
                    "default": False
                },
                "set_upstream": {
                    "type": "boolean",
                    "description": "Set upstream tracking branch",
                    "default": False
                }
            },
            "required": [],
            "additionalProperties": False
        } 