"""GitHub repositories listing command."""

import asyncio
import json
from typing import Dict, Any, Optional
from mcp_proxy_adapter.commands.base import Command
from mcp_proxy_adapter.commands.result import SuccessResult, ErrorResult
from mcp_proxy_adapter.config import config


class GitHubListReposCommand(Command):
    """List GitHub repositories for the authenticated user."""
    
    name = "github_list_repos"
    
    async def execute(
        self,
        type: str = "owner",
        sort: str = "updated",
        direction: str = "desc",
        per_page: int = 30,
        page: int = 1,
        username: Optional[str] = None,
        token: Optional[str] = None,
        **kwargs
    ) -> SuccessResult:
        """List GitHub repositories.
        
        Args:
            type: Type of repositories ('all', 'owner', 'public', 'private', 'member')
            sort: Sort by ('created', 'updated', 'pushed', 'full_name')
            direction: Sort direction ('asc', 'desc')
            per_page: Number of results per page (1-100)
            page: Page number
            username: GitHub username (optional, reads from config)
            token: GitHub Personal Access Token (optional, reads from config)
            
        Returns:
            SuccessResult with repositories list
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
            
            # Validate parameters
            valid_types = ["all", "owner", "public", "private", "member"]
            if type not in valid_types:
                return ErrorResult(
                    message=f"Invalid type. Must be one of: {', '.join(valid_types)}",
                    code="INVALID_TYPE",
                    details={"type": type, "valid_types": valid_types}
                )
            
            valid_sorts = ["created", "updated", "pushed", "full_name"]
            if sort not in valid_sorts:
                return ErrorResult(
                    message=f"Invalid sort. Must be one of: {', '.join(valid_sorts)}",
                    code="INVALID_SORT",
                    details={"sort": sort, "valid_sorts": valid_sorts}
                )
            
            if direction not in ["asc", "desc"]:
                return ErrorResult(
                    message="Invalid direction. Must be 'asc' or 'desc'",
                    code="INVALID_DIRECTION",
                    details={"direction": direction}
                )
            
            if not (1 <= per_page <= 100):
                return ErrorResult(
                    message="per_page must be between 1 and 100",
                    code="INVALID_PER_PAGE",
                    details={"per_page": per_page}
                )
            
            # Build API URL with parameters
            api_url = f"https://api.github.com/user/repos?type={type}&sort={sort}&direction={direction}&per_page={per_page}&page={page}"
            
            # Create curl command for GitHub API
            cmd_args = [
                "curl",
                "-H", "Accept: application/vnd.github.v3+json",
                "-H", f"Authorization: token {token}",
                api_url
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
                        "exit_code": process.returncode
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
            if isinstance(response, dict) and "message" in response:
                return ErrorResult(
                    message=f"GitHub API error: {response['message']}",
                    code="GITHUB_API_ERROR",
                    details={
                        "api_message": response["message"],
                        "documentation_url": response.get("documentation_url")
                    }
                )
            
            # Process repositories
            repositories = []
            for repo in response:
                repositories.append({
                    "name": repo.get("name"),
                    "full_name": repo.get("full_name"),
                    "description": repo.get("description"),
                    "private": repo.get("private"),
                    "html_url": repo.get("html_url"),
                    "clone_url": repo.get("clone_url"),
                    "ssh_url": repo.get("ssh_url"),
                    "language": repo.get("language"),
                    "size": repo.get("size"),
                    "stargazers_count": repo.get("stargazers_count"),
                    "watchers_count": repo.get("watchers_count"),
                    "forks_count": repo.get("forks_count"),
                    "created_at": repo.get("created_at"),
                    "updated_at": repo.get("updated_at"),
                    "pushed_at": repo.get("pushed_at"),
                    "default_branch": repo.get("default_branch")
                })
            
            # Success response
            return SuccessResult(data={
                "status": "success",
                "message": f"Retrieved {len(repositories)} repositories",
                "repositories": repositories,
                "pagination": {
                    "page": page,
                    "per_page": per_page,
                    "total_found": len(repositories)
                },
                "filters": {
                    "type": type,
                    "sort": sort,
                    "direction": direction
                },
                "summary": {
                    "total_repositories": len(repositories),
                    "private_count": sum(1 for repo in repositories if repo["private"]),
                    "public_count": sum(1 for repo in repositories if not repo["private"]),
                    "languages": list(set(repo["language"] for repo in repositories if repo["language"]))
                }
            })
            
        except Exception as e:
            return ErrorResult(
                message=f"Unexpected error listing repositories: {str(e)}",
                code="UNEXPECTED_ERROR",
                details={"error_type": type(e).__name__}
            )
    
    @classmethod
    def get_schema(cls) -> Dict[str, Any]:
        """Get the JSON schema for this command."""
        return {
            "type": "object",
            "properties": {
                "type": {
                    "type": "string",
                    "description": "Type of repositories to list",
                    "enum": ["all", "owner", "public", "private", "member"],
                    "default": "owner"
                },
                "sort": {
                    "type": "string",
                    "description": "Sort repositories by",
                    "enum": ["created", "updated", "pushed", "full_name"],
                    "default": "updated"
                },
                "direction": {
                    "type": "string",
                    "description": "Sort direction",
                    "enum": ["asc", "desc"],
                    "default": "desc"
                },
                "per_page": {
                    "type": "integer",
                    "description": "Number of results per page (1-100)",
                    "minimum": 1,
                    "maximum": 100,
                    "default": 30
                },
                "page": {
                    "type": "integer",
                    "description": "Page number",
                    "minimum": 1,
                    "default": 1
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
            "required": [],
            "additionalProperties": False
        } 