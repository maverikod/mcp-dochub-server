"""GitHub repository creation command."""

import asyncio
import json
from typing import Dict, Any, Optional
from mcp_proxy_adapter.commands.base import Command
from mcp_proxy_adapter.commands.result import SuccessResult, ErrorResult
from mcp_proxy_adapter.core.errors import CommandError, ValidationError
from mcp_proxy_adapter.config import config


class GitHubCreateRepoCommand(Command):
    """Create a new GitHub repository using GitHub API."""
    
    name = "github_create_repo"
    
    async def execute(
        self,
        repo_name: str,
        description: str = "",
        private: bool = False,
        initialize: bool = True,
        gitignore_template: Optional[str] = None,
        license_template: Optional[str] = None,
        username: Optional[str] = None,
        token: Optional[str] = None,
        **kwargs
    ) -> SuccessResult:
        """Create a new GitHub repository.
        
        Args:
            repo_name: Name of the repository
            description: Repository description
            private: Make repository private (default: False)
            initialize: Initialize with README (default: True)
            gitignore_template: Add .gitignore template (e.g., "Python", "Node")
            license_template: Add license (e.g., "mit", "apache-2.0")
            username: GitHub username (optional, reads from config)
            token: GitHub Personal Access Token (optional, reads from config)
            
        Returns:
            SuccessResult with repository information
        """
        try:
            # Read from config if parameters not provided
            if not username:
                username = config.get("github.username")
            if not token:
                token = config.get("github.token")
                
            if not username or not token:
                return ErrorResult(
                    message="GitHub username and token are required",
                    code="MISSING_CREDENTIALS",
                    details={
                        "username_provided": bool(username),
                        "token_provided": bool(token),
                        "config_note": "Set github.username and github.token in config.json"
                    }
                )
            
            # Validate repository name
            if not repo_name or not repo_name.replace("-", "").replace("_", "").replace(".", "").isalnum():
                return ErrorResult(
                    message="Invalid repository name. Use only letters, numbers, hyphens, underscores, and periods.",
                    code="INVALID_REPO_NAME",
                    details={"repo_name": repo_name}
                )
            
            # Prepare repository data
            repo_data = {
                "name": repo_name,
                "description": description,
                "private": private,
                "auto_init": initialize
            }
            
            if gitignore_template:
                repo_data["gitignore_template"] = gitignore_template
                
            if license_template:
                repo_data["license_template"] = license_template
            
            # Create curl command for GitHub API
            cmd_args = [
                "curl",
                "-X", "POST",
                "-H", "Accept: application/vnd.github.v3+json",
                "-H", f"Authorization: token {token}",
                "-H", "Content-Type: application/json",
                "https://api.github.com/user/repos",
                "-d", json.dumps(repo_data)
            ]
            
            # Execute API call
            process = await asyncio.create_subprocess_exec(
                *cmd_args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                error_msg = stderr.decode('utf-8').strip()
                return ErrorResult(
                    message=f"GitHub API request failed: {error_msg}",
                    code="API_ERROR",
                    details={
                        "stderr": error_msg,
                        "exit_code": process.returncode,
                        "repo_name": repo_name
                    }
                )
            
            # Parse response
            try:
                response = json.loads(stdout.decode('utf-8'))
            except json.JSONDecodeError as e:
                return ErrorResult(
                    message=f"Failed to parse GitHub API response: {str(e)}",
                    code="PARSE_ERROR",
                    details={"raw_response": stdout.decode('utf-8')[:500]}
                )
            
            # Check for API errors
            if "message" in response and "errors" in response:
                return ErrorResult(
                    message=f"GitHub API error: {response['message']}",
                    code="GITHUB_API_ERROR",
                    details={
                        "api_message": response["message"],
                        "errors": response.get("errors", []),
                        "repo_name": repo_name
                    }
                )
            
            # Success response
            return SuccessResult(data={
                "status": "success",
                "message": f"Repository '{repo_name}' created successfully",
                "repository": {
                    "name": response.get("name"),
                    "full_name": response.get("full_name"),
                    "description": response.get("description"),
                    "private": response.get("private"),
                    "html_url": response.get("html_url"),
                    "clone_url": response.get("clone_url"),
                    "ssh_url": response.get("ssh_url"),
                    "created_at": response.get("created_at"),
                    "size": response.get("size", 0)
                },
                "options": {
                    "private": private,
                    "initialize": initialize,
                    "gitignore_template": gitignore_template,
                    "license_template": license_template
                },
                "timestamp": response.get("created_at")
            })
            
        except Exception as e:
            return ErrorResult(
                message=f"Unexpected error creating repository: {str(e)}",
                code="UNEXPECTED_ERROR",
                details={"error_type": type(e).__name__}
            )
    
    @classmethod
    def get_schema(cls) -> Dict[str, Any]:
        """Get the JSON schema for this command."""
        return {
            "type": "object",
            "properties": {
                "repo_name": {
                    "type": "string",
                    "description": "Name of the repository (required)",
                    "pattern": "^[a-zA-Z0-9._-]+$"
                },
                "description": {
                    "type": "string",
                    "description": "Repository description",
                    "default": ""
                },
                "private": {
                    "type": "boolean",
                    "description": "Make repository private",
                    "default": False
                },
                "initialize": {
                    "type": "boolean",
                    "description": "Initialize repository with README",
                    "default": True
                },
                "gitignore_template": {
                    "type": "string",
                    "description": "Add .gitignore template (e.g., 'Python', 'Node', 'Java')"
                },
                "license_template": {
                    "type": "string",
                    "description": "Add license template (e.g., 'mit', 'apache-2.0', 'gpl-3.0')"
                },
                "username": {
                    "type": "string",
                    "description": "GitHub username (optional, reads from config if not provided)"
                },
                "token": {
                    "type": "string",
                    "description": "GitHub Personal Access Token (optional, reads from config if not provided)"
                }
            },
            "required": ["repo_name"],
            "additionalProperties": False
        } 