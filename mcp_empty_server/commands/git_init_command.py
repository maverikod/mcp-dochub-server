"""Git init command."""

import asyncio
import os
from typing import Dict, Any, Optional
from mcp_proxy_adapter.commands.base import Command
from mcp_proxy_adapter.commands.result import SuccessResult, ErrorResult


class GitInitCommand(Command):
    """Initialize a Git repository."""
    
    name = "git_init"
    
    async def execute(
        self,
        directory: Optional[str] = None,
        bare: bool = False,
        initial_branch: Optional[str] = None,
        **kwargs
    ) -> SuccessResult:
        """Initialize a Git repository.
        
        Args:
            directory: Directory to initialize (defaults to current directory)
            bare: Create a bare repository
            initial_branch: Set initial branch name (e.g., 'main')
            
        Returns:
            SuccessResult with initialization information
        """
        try:
            # Set working directory
            work_dir = directory if directory else os.getcwd()
            
            # Check if directory exists
            if not os.path.exists(work_dir):
                return ErrorResult(
                    message=f"Directory '{work_dir}' does not exist",
                    code="DIRECTORY_NOT_FOUND",
                    details={"directory": work_dir}
                )
            
            # Build git init command
            cmd_args = ["git", "init"]
            
            if bare:
                cmd_args.append("--bare")
            
            if initial_branch:
                cmd_args.extend(["--initial-branch", initial_branch])
            
            if directory:
                cmd_args.append(directory)
            
            # Execute git init
            process = await asyncio.create_subprocess_exec(
                *cmd_args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=work_dir if not directory else os.getcwd()
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                error_msg = stderr.decode('utf-8').strip()
                return ErrorResult(
                    message=f"Git init failed: {error_msg}",
                    code="INIT_ERROR",
                    details={
                        "stderr": error_msg,
                        "exit_code": process.returncode,
                        "directory": work_dir,
                        "command": " ".join(cmd_args)
                    }
                )
            
            # Get repository information
            repo_info = {
                "directory": os.path.abspath(work_dir),
                "bare": bare,
                "initial_branch": initial_branch
            }
            
            # Check if .git exists and get more info
            git_dir = os.path.join(work_dir, ".git")
            if os.path.exists(git_dir):
                repo_info["git_directory"] = git_dir
                repo_info["is_bare"] = False
            elif bare:
                repo_info["is_bare"] = True
                repo_info["git_directory"] = work_dir
            
            # Success response
            return SuccessResult(data={
                "status": "success",
                "message": f"Git repository initialized in '{work_dir}'",
                "repository": repo_info,
                "options": {
                    "bare": bare,
                    "initial_branch": initial_branch,
                    "directory": directory
                },
                "command": " ".join(cmd_args),
                "output": stdout.decode('utf-8').strip()
            })
            
        except Exception as e:
            return ErrorResult(
                message=f"Unexpected error during git init: {str(e)}",
                code="UNEXPECTED_ERROR",
                details={"error_type": type(e).__name__}
            )
    
    @classmethod
    def get_schema(cls) -> Dict[str, Any]:
        """Get the JSON schema for this command."""
        return {
            "type": "object",
            "properties": {
                "directory": {
                    "type": "string",
                    "description": "Directory to initialize (optional, defaults to current directory)"
                },
                "bare": {
                    "type": "boolean",
                    "description": "Create a bare repository",
                    "default": False
                },
                "initial_branch": {
                    "type": "string",
                    "description": "Set initial branch name (e.g., 'main')"
                }
            },
            "required": [],
            "additionalProperties": False
        } 