"""Docker tag command for tagging container images."""

import asyncio
from typing import Dict, Any
from datetime import datetime
from mcp_proxy_adapter.commands.base import Command
from mcp_proxy_adapter.commands.result import SuccessResult, ErrorResult
from mcp_proxy_adapter.core.errors import CommandError, ValidationError


class DockerTagCommand(Command):
    """Tag Docker images with new repository names and tags.
    
    This command creates new tags for existing Docker images,
    which is useful for preparing images for pushing to registries.
    """
    
    name = "docker_tag"
    
    async def execute(
        self,
        source_image: str,
        target_image: str,
        **kwargs
    ) -> SuccessResult:
        """Execute Docker tag command.
        
        Args:
            source_image: Source image name with tag (e.g., 'myapp:latest')
            target_image: Target image name with tag (e.g., 'username/myapp:v1.0.0')
            
        Returns:
            Success result with tagging information
        """
        try:
            # Validate inputs
            if not source_image:
                raise ValidationError("Source image is required")
            
            if not target_image:
                raise ValidationError("Target image is required")
            
            # Build Docker tag command
            cmd = ["docker", "tag", source_image, target_image]
            
            # Execute tag command
            start_time = datetime.now()
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            end_time = datetime.now()
            
            if process.returncode != 0:
                error_output = stderr.decode('utf-8')
                raise CommandError(
                    f"Docker tag failed with exit code {process.returncode}",
                    details={
                        "stderr": error_output,
                        "stdout": stdout.decode('utf-8'),
                        "command": " ".join(cmd),
                        "exit_code": process.returncode,
                        "source_image": source_image,
                        "target_image": target_image
                    }
                )
            
            return SuccessResult(data={
                "status": "success",
                "message": "Docker image tagged successfully",
                "source_image": source_image,
                "target_image": target_image,
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
                code="TAG_ERROR",
                details=e.data
            )
        except Exception as e:
            return ErrorResult(
                message=f"Unexpected error during Docker tag: {str(e)}",
                code="INTERNAL_ERROR",
                details={"error_type": "unexpected", "error": str(e)}
            )
    
    @classmethod
    def get_schema(cls) -> Dict[str, Any]:
        """Get JSON schema for Docker tag command parameters."""
        return {
            "type": "object",
            "properties": {
                "source_image": {
                    "type": "string",
                    "description": "Source image name with tag (e.g., 'myapp:latest')",
                    "examples": ["myapp:latest", "nginx:alpine", "ubuntu:20.04"]
                },
                "target_image": {
                    "type": "string",
                    "description": "Target image name with tag (e.g., 'username/myapp:v1.0.0')",
                    "examples": ["username/myapp:v1.0.0", "registry.com/namespace/app:latest"]
                }
            },
            "required": ["source_image", "target_image"],
            "additionalProperties": False
        } 