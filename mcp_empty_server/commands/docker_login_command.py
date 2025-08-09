"""Docker login command for authenticating with Docker registries."""

import asyncio
import os
import subprocess
from typing import Dict, Any, Optional
from datetime import datetime
from mcp_proxy_adapter.commands.base import Command
from mcp_proxy_adapter.commands.result import SuccessResult, ErrorResult
from mcp_proxy_adapter.core.errors import CommandError, ValidationError
from mcp_proxy_adapter.config import config


class DockerLoginCommand(Command):
    """Authenticate with Docker registries including Docker Hub.
    
    This command allows logging into Docker registries with username/password
    or using access tokens for secure authentication. If no parameters provided,
    reads credentials from configuration file.
    """
    
    name = "docker_login"
    
    async def execute(
        self,
        username: Optional[str] = None,
        password: Optional[str] = None,
        token: Optional[str] = None,
        registry: Optional[str] = None,
        password_stdin: bool = False,
        **kwargs
    ) -> SuccessResult:
        """Execute Docker login command.
        
        Args:
            username: Docker Hub username (optional, reads from config if not provided)
            password: Docker Hub password (use token instead for security)
            token: Access token (recommended over password, reads from config if not provided)
            registry: Registry URL (optional, reads from config if not provided)
            password_stdin: Read password from stdin
            
        Returns:
            Success result with login information
        """
        try:
            # Read from config if parameters not provided
            if not username:
                username = config.get("docker.username")
            if not token and not password:
                token = config.get("docker.token")
            if not registry:
                registry = config.get("docker.registry", "docker.io")
            
            # Validate inputs
            if not username:
                raise ValidationError("Username is required (provide directly or in config)")
            
            if not password and not token and not password_stdin:
                raise ValidationError("Either password, token, or password_stdin must be provided (or token in config)")
            
            if password and token:
                raise ValidationError("Cannot use both password and token, choose one")
            
            # Build Docker login command
            cmd = ["docker", "login"]
            
            # Add registry if not default
            if registry and registry != "docker.io":
                cmd.append(registry)
            
            # Add username
            cmd.extend(["-u", username])
            
            # Prepare authentication
            auth_method = None
            stdin_input = None
            
            if password_stdin:
                cmd.append("--password-stdin")
                auth_method = "password_stdin"
                if password:
                    stdin_input = password
                elif token:
                    stdin_input = token
                else:
                    raise ValidationError("Password or token required when using password_stdin")
            elif token:
                cmd.extend(["-p", token])
                auth_method = "token"
            elif password:
                cmd.extend(["-p", password])
                auth_method = "password"
            
            # Execute login command
            start_time = datetime.now()
            
            if password_stdin and stdin_input:
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdin=asyncio.subprocess.PIPE,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, stderr = await process.communicate(input=stdin_input.encode())
            else:
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, stderr = await process.communicate()
            
            end_time = datetime.now()
            
            if process.returncode != 0:
                error_msg = stderr.decode('utf-8').strip()
                return ErrorResult(
                    message=f"Docker login failed: {error_msg}",
                    code="LOGIN_ERROR",
                    details={
                        "stderr": error_msg,
                        "exit_code": process.returncode,
                        "registry": registry,
                        "username": username
                    }
                )
            
            # Parse success output
            output = stdout.decode('utf-8').strip()
            
            return SuccessResult(data={
                "status": "success",
                "message": "Successfully logged in to Docker registry",
                "registry": registry,
                "username": username,
                "auth_method": auth_method,
                "login_time": end_time.isoformat(),
                "output": output,
                "config_used": {
                    "username_from_config": not bool(kwargs.get('username')),
                    "token_from_config": not bool(kwargs.get('token')) and not bool(kwargs.get('password')),
                    "registry_from_config": not bool(kwargs.get('registry'))
                }
            })
            
        except ValidationError as e:
            return ErrorResult(
                message=str(e),
                code="VALIDATION_ERROR",
                details={"error_type": "validation"}
            )
        except CommandError as e:
            return ErrorResult(
                message=str(e),
                code="LOGIN_ERROR",
                details={"error_type": "command_error"}
            )
        except Exception as e:
            return ErrorResult(
                message=f"Unexpected error during Docker login: {str(e)}",
                code="INTERNAL_ERROR",
                details={"error_type": "unexpected", "error": str(e)}
            )
    
    @classmethod
    def get_schema(cls) -> Dict[str, Any]:
        """Get JSON schema for Docker login command parameters."""
        return {
            "type": "object",
            "properties": {
                "username": {
                    "type": "string",
                    "description": "Docker Hub username (optional, reads from config if not provided)"
                },
                "password": {
                    "type": "string",
                    "description": "Docker Hub password (not recommended, use token instead)",
                    "format": "password"
                },
                "token": {
                    "type": "string",
                    "description": "Access token (recommended for security, reads from config if not provided)",
                    "format": "password"
                },
                "registry": {
                    "type": "string",
                    "description": "Registry URL (optional, reads from config if not provided)",
                    "examples": ["docker.io", "ghcr.io", "registry.gitlab.com"]
                },
                "password_stdin": {
                    "type": "boolean",
                    "description": "Read password from stdin (more secure)",
                    "default": False
                }
            },
            "required": [],
            "additionalProperties": False
        } 