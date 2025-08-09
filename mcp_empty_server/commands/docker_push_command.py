"""Docker push command for uploading images to registries."""

import asyncio
import subprocess
from typing import Dict, Any, Optional, List
from datetime import datetime
from mcp_proxy_adapter.commands.base import Command
from mcp_proxy_adapter.commands.result import SuccessResult, ErrorResult
from mcp_proxy_adapter.core.errors import CommandError, ValidationError


class DockerPushCommand(Command):
    """Push Docker images to registries like Docker Hub.
    
    This command uploads Docker images to container registries with
    support for multiple tags and platforms.
    """
    
    name = "docker_push"
    
    async def execute(
        self,
        image_name: str,
        tag: str = "latest",
        all_tags: bool = False,
        disable_content_trust: bool = False,
        quiet: bool = False,
        **kwargs
    ) -> SuccessResult:
        """Execute Docker push command.
        
        Args:
            image_name: Name of the image to push (e.g., 'username/myapp')
            tag: Tag to push (default: 'latest')
            all_tags: Push all tags of the image
            disable_content_trust: Skip image signing (default: False)
            quiet: Suppress verbose output
            
        Returns:
            Success result with push information
        """
        try:
            # Validate inputs
            if not image_name:
                raise ValidationError("Image name is required")
            
            # Construct full image name
            if all_tags:
                full_image_name = image_name
            else:
                full_image_name = f"{image_name}:{tag}"
            
            # Build Docker push command
            cmd = ["docker", "push"]
            
            # Add options
            if all_tags:
                cmd.append("--all-tags")
            
            if disable_content_trust:
                cmd.append("--disable-content-trust")
            
            if quiet:
                cmd.append("--quiet")
            
            # Add image name
            cmd.append(full_image_name)
            
            # Execute push command
            start_time = datetime.now()
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            end_time = datetime.now()
            push_duration = (end_time - start_time).total_seconds()
            
            if process.returncode != 0:
                error_output = stderr.decode('utf-8')
                raise CommandError(
                    f"Docker push failed with exit code {process.returncode}",
                    details={
                        "stderr": error_output,
                        "stdout": stdout.decode('utf-8'),
                        "command": " ".join(cmd),
                        "exit_code": process.returncode
                    }
                )
            
            # Parse output for digest and size information
            output_lines = stdout.decode('utf-8').splitlines()
            digest = None
            size_info = []
            
            for line in output_lines:
                if "digest:" in line:
                    digest = line.split("digest: ")[-1].strip()
                elif "Pushed" in line or "Mounted" in line:
                    size_info.append(line.strip())
            
            return SuccessResult(data={
                "status": "success",
                "message": "Docker image pushed successfully",
                "image_name": image_name,
                "tag": tag if not all_tags else "all",
                "full_image_name": full_image_name,
                "digest": digest,
                "push_duration_seconds": push_duration,
                "size_info": size_info,
                "options": {
                    "all_tags": all_tags,
                    "disable_content_trust": disable_content_trust,
                    "quiet": quiet
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
                code="PUSH_ERROR",
                details=e.data
            )
        except Exception as e:
            return ErrorResult(
                message=f"Unexpected error during Docker push: {str(e)}",
                code="INTERNAL_ERROR",
                details={"error_type": "unexpected", "error": str(e)}
            )
    
    @classmethod
    def get_schema(cls) -> Dict[str, Any]:
        """Get JSON schema for Docker push command parameters."""
        return {
            "type": "object",
            "properties": {
                "image_name": {
                    "type": "string",
                    "description": "Name of the image to push (e.g., 'username/myapp')",
                    "pattern": "^[a-z0-9]+(?:[._-][a-z0-9]+)*(?:/[a-z0-9]+(?:[._-][a-z0-9]+)*)*$",
                    "examples": ["myusername/myapp", "registry.com/namespace/app"]
                },
                "tag": {
                    "type": "string",
                    "description": "Tag to push",
                    "default": "latest",
                    "examples": ["latest", "v1.0.0", "dev", "prod"]
                },
                "all_tags": {
                    "type": "boolean",
                    "description": "Push all tags of the image",
                    "default": False
                },
                "disable_content_trust": {
                    "type": "boolean",
                    "description": "Skip image signing",
                    "default": False
                },
                "quiet": {
                    "type": "boolean",
                    "description": "Suppress verbose output",
                    "default": False
                }
            },
            "required": ["image_name"],
            "additionalProperties": False
        } 