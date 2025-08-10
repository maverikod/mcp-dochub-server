"""Docker build command for building container images."""

import asyncio
import os
from typing import Dict, Any, Optional
from datetime import datetime
from mcp_proxy_adapter.commands.base import Command
from mcp_proxy_adapter.commands.result import SuccessResult, ErrorResult
from mcp_proxy_adapter.core.errors import CommandError, ValidationError


class DockerBuildCommand(Command):
    """Build Docker images from Dockerfile.
    
    This command allows building Docker images with various options
    including tagging, build context, and build arguments.
    """
    
    name = "docker_build"
    
    async def execute(
        self,
        dockerfile_path: str = "Dockerfile",
        tag: Optional[str] = None,
        context_path: str = ".",
        build_args: Optional[Dict[str, str]] = None,
        no_cache: bool = False,
        platform: Optional[str] = None,
        target: Optional[str] = None,
        **kwargs
    ) -> SuccessResult:
        """Execute Docker build command.
        
        Args:
            dockerfile_path: Path to Dockerfile (relative to context)
            tag: Tag for the built image (e.g., 'myapp:latest')
            context_path: Build context path
            build_args: Build arguments as key-value pairs
            no_cache: Don't use cache when building the image
            platform: Target platform for build (e.g., 'linux/amd64')
            target: Target build stage for multi-stage builds
            
        Returns:
            Success result with build information
        """
        try:
            # Validate inputs
            if not os.path.exists(context_path):
                raise ValidationError(f"Build context path does not exist: {context_path}")
            
            dockerfile_full_path = os.path.join(context_path, dockerfile_path)
            if not os.path.exists(dockerfile_full_path):
                raise ValidationError(f"Dockerfile does not exist: {dockerfile_full_path}")
            
            # Build Docker command
            cmd = ["docker", "build"]
            
            # Add dockerfile path
            cmd.extend(["-f", dockerfile_path])
            
            # Add tag if specified
            if tag:
                cmd.extend(["-t", tag])
            
            # Add build arguments
            if build_args:
                for key, value in build_args.items():
                    cmd.extend(["--build-arg", f"{key}={value}"])
            
            # Add no-cache option
            if no_cache:
                cmd.append("--no-cache")
            
            # Add platform if specified
            if platform:
                cmd.extend(["--platform", platform])
            
            # Add target if specified (for multi-stage builds)
            if target:
                cmd.extend(["--target", target])
            
            # Add context path
            cmd.append(context_path)
            
            # Execute build command
            start_time = datetime.now()
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=os.getcwd()
            )
            
            stdout, stderr = await process.communicate()
            end_time = datetime.now()
            build_duration = (end_time - start_time).total_seconds()
            
            if process.returncode != 0:
                raise CommandError(
                    f"Docker build failed with exit code {process.returncode}",
                    details={
                        "stdout": stdout.decode('utf-8'),
                        "stderr": stderr.decode('utf-8'),
                        "command": " ".join(cmd)
                    }
                )
            
            # Parse output for image ID
            output_lines = stdout.decode('utf-8').splitlines()
            image_id = None
            for line in output_lines:
                if line.startswith("Successfully built"):
                    image_id = line.split()[-1]
                    break
            
            return SuccessResult(data={
                "status": "success",
                "message": "Docker image built successfully",
                "image_id": image_id,
                "tag": tag,
                "build_duration_seconds": build_duration,
                "dockerfile_path": dockerfile_path,
                "context_path": context_path,
                "build_args": build_args or {},
                "build_options": {
                    "no_cache": no_cache,
                    "platform": platform,
                    "target": target
                },
                "command": " ".join(cmd),
                "timestamp": end_time.isoformat()
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
                code="BUILD_ERROR",
                details=e.data
            )
        except Exception as e:
            return ErrorResult(
                message=f"Unexpected error during Docker build: {str(e)}",
                code="INTERNAL_ERROR",
                details={"error_type": "unexpected", "error": str(e)}
            )
    
    @classmethod
    def get_schema(cls) -> Dict[str, Any]:
        """Get JSON schema for Docker build command parameters."""
        return {
            "type": "object",
            "properties": {
                "dockerfile_path": {
                    "type": "string",
                    "description": "Path to Dockerfile relative to context",
                    "default": "Dockerfile"
                },
                "tag": {
                    "type": "string",
                    "description": "Tag for the built image (e.g., 'myapp:latest')",
                    "examples": ["myapp:latest", "username/myapp:v1.0.0"]
                },
                "context_path": {
                    "type": "string",
                    "description": "Build context path",
                    "default": "."
                },
                "build_args": {
                    "type": "object",
                    "description": "Build arguments as key-value pairs",
                    "additionalProperties": {"type": "string"},
                    "examples": [{"VERSION": "1.0.0", "ENV": "production"}]
                },
                "no_cache": {
                    "type": "boolean",
                    "description": "Don't use cache when building the image",
                    "default": False
                },
                "platform": {
                    "type": "string",
                    "description": "Target platform for build",
                    "examples": ["linux/amd64", "linux/arm64", "linux/arm/v7"]
                },
                "target": {
                    "type": "string",
                    "description": "Target build stage for multi-stage builds",
                    "examples": ["development", "production", "testing"]
                }
            },
            "required": [],
            "additionalProperties": False
        } 