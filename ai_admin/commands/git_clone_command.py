"""Git clone command."""

import asyncio
import os
from typing import Dict, Any, Optional
from mcp_proxy_adapter.commands.base import Command
from mcp_proxy_adapter.commands.result import SuccessResult, ErrorResult


class GitCloneCommand(Command):
    """Clone a Git repository."""
    
    name = "git_clone"
    
    async def execute(
        self,
        repository_url: str,
        destination: Optional[str] = None,
        branch: Optional[str] = None,
        depth: Optional[int] = None,
        recursive: bool = False,
        **kwargs
    ) -> SuccessResult:
        """Clone a Git repository.
        
        Args:
            repository_url: Git repository URL (HTTP/HTTPS or SSH)
            destination: Destination directory (optional, uses repo name if not provided)
            branch: Specific branch to clone
            depth: Create a shallow clone with history truncated to specified number of commits
            recursive: Recursively clone submodules
            
        Returns:
            SuccessResult with clone information
        """
        try:
            # Validate repository URL
            if not repository_url:
                return ErrorResult(
                    message="Repository URL is required",
                    code="MISSING_REPOSITORY_URL",
                    details={}
                )
            
            # Determine destination directory
            if not destination:
                # Extract repository name from URL
                repo_name = repository_url.rstrip('/').split('/')[-1]
                if repo_name.endswith('.git'):
                    repo_name = repo_name[:-4]
                destination = repo_name
            
            # Check if destination already exists
            if os.path.exists(destination):
                return ErrorResult(
                    message=f"Destination directory '{destination}' already exists",
                    code="DESTINATION_EXISTS",
                    details={
                        "destination": destination,
                        "exists": True
                    }
                )
            
            # Build git clone command
            cmd_args = ["git", "clone"]
            
            if branch:
                cmd_args.extend(["--branch", branch])
            
            if depth is not None:
                if depth < 1:
                    return ErrorResult(
                        message="Depth must be a positive integer",
                        code="INVALID_DEPTH",
                        details={"depth": depth}
                    )
                cmd_args.extend(["--depth", str(depth)])
            
            if recursive:
                cmd_args.append("--recursive")
            
            cmd_args.extend([repository_url, destination])
            
            # Execute git clone
            process = await asyncio.create_subprocess_exec(
                *cmd_args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=os.getcwd()
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                error_msg = stderr.decode('utf-8').strip()
                return ErrorResult(
                    message=f"Git clone failed: {error_msg}",
                    code="CLONE_ERROR",
                    details={
                        "stderr": error_msg,
                        "exit_code": process.returncode,
                        "repository_url": repository_url,
                        "destination": destination,
                        "command": " ".join(cmd_args)
                    }
                )
            
            # Get repository information
            repo_info = {
                "destination": os.path.abspath(destination),
                "repository_url": repository_url,
                "branch": branch,
                "depth": depth,
                "recursive": recursive
            }
            
            # Try to get actual branch info
            try:
                # Get current branch
                branch_process = await asyncio.create_subprocess_exec(
                    "git", "branch", "--show-current",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=destination
                )
                branch_stdout, _ = await branch_process.communicate()
                if branch_process.returncode == 0:
                    current_branch = branch_stdout.decode('utf-8').strip()
                    repo_info["current_branch"] = current_branch
                
                # Get remote info
                remote_process = await asyncio.create_subprocess_exec(
                    "git", "remote", "-v",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=destination
                )
                remote_stdout, _ = await remote_process.communicate()
                if remote_process.returncode == 0:
                    repo_info["remotes"] = remote_stdout.decode('utf-8').strip()
                
                # Get latest commit info
                log_process = await asyncio.create_subprocess_exec(
                    "git", "log", "-1", "--oneline",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=destination
                )
                log_stdout, _ = await log_process.communicate()
                if log_process.returncode == 0:
                    repo_info["latest_commit"] = log_stdout.decode('utf-8').strip()
                    
            except Exception:
                # If any git info command fails, continue without that info
                pass
            
            # Success response
            return SuccessResult(data={
                "status": "success",
                "message": f"Repository cloned successfully to '{destination}'",
                "repository": repo_info,
                "options": {
                    "branch": branch,
                    "depth": depth,
                    "recursive": recursive
                },
                "command": " ".join(cmd_args),
                "output": stdout.decode('utf-8').strip()
            })
            
        except Exception as e:
            return ErrorResult(
                message=f"Unexpected error during clone: {str(e)}",
                code="UNEXPECTED_ERROR",
                details={"error_type": type(e).__name__}
            )
    
    @classmethod
    def get_schema(cls) -> Dict[str, Any]:
        """Get the JSON schema for this command."""
        return {
            "type": "object",
            "properties": {
                "repository_url": {
                    "type": "string",
                    "description": "Git repository URL (HTTP/HTTPS or SSH)",
                    "pattern": r"^(https?://|git@|ssh://)",
                    "examples": [
                        "https://github.com/user/repo.git",
                        "git@github.com:user/repo.git"
                    ]
                },
                "destination": {
                    "type": "string",
                    "description": "Destination directory (optional, uses repo name if not provided)"
                },
                "branch": {
                    "type": "string",
                    "description": "Specific branch to clone"
                },
                "depth": {
                    "type": "integer",
                    "description": "Create shallow clone with specified depth",
                    "minimum": 1
                },
                "recursive": {
                    "type": "boolean",
                    "description": "Recursively clone submodules",
                    "default": False
                }
            },
            "required": ["repository_url"],
            "additionalProperties": False
        } 