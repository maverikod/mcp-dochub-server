"""Docker remove command for deleting container images."""

import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime
from mcp_proxy_adapter.commands.base import Command
from mcp_proxy_adapter.commands.result import SuccessResult, ErrorResult
from mcp_proxy_adapter.core.errors import CommandError, ValidationError


class DockerRemoveCommand(Command):
    """Remove Docker images from the local system.
    
    This command deletes Docker images by image ID, repository:tag,
    or repository name with support for force removal.
    """
    
    name = "docker_rmi"
    
    async def execute(
        self,
        images: List[str],
        force: bool = False,
        no_prune: bool = False,
        **kwargs
    ) -> SuccessResult:
        """Execute Docker remove images command.
        
        Args:
            images: List of image names, IDs, or tags to remove
            force: Force removal of the image
            no_prune: Do not delete untagged parents
            
        Returns:
            Success result with removal information
        """
        try:
            # Validate inputs
            if not images:
                raise ValidationError("At least one image must be specified")
            
            if not isinstance(images, list):
                raise ValidationError("Images must be provided as a list")
            
            # Build Docker rmi command
            cmd = ["docker", "rmi"]
            
            # Add options
            if force:
                cmd.append("--force")
            
            if no_prune:
                cmd.append("--no-prune")
            
            # Add images
            cmd.extend(images)
            
            # Execute remove command
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
                
                # Check if it's a partial failure (some images removed, some failed)
                success_output = stdout.decode('utf-8')
                
                raise CommandError(
                    f"Docker rmi failed with exit code {process.returncode}",
                    data={
                        "stderr": error_output,
                        "stdout": success_output,
                        "command": " ".join(cmd),
                        "exit_code": process.returncode,
                        "requested_images": images
                    }
                )
            
            # Parse successful output
            output_lines = stdout.decode('utf-8').strip().splitlines()
            removed_items = []
            
            for line in output_lines:
                line = line.strip()
                if line.startswith("Untagged:"):
                    removed_items.append({
                        "action": "untagged",
                        "item": line.replace("Untagged: ", "")
                    })
                elif line.startswith("Deleted:"):
                    removed_items.append({
                        "action": "deleted",
                        "item": line.replace("Deleted: ", "")
                    })
                elif line:
                    removed_items.append({
                        "action": "removed",
                        "item": line
                    })
            
            return SuccessResult(data={
                "status": "success",
                "message": f"Successfully removed {len(images)} image(s)",
                "requested_images": images,
                "removed_items": removed_items,
                "options": {
                    "force": force,
                    "no_prune": no_prune
                },
                "command": " ".join(cmd),
                "timestamp": end_time.isoformat()
            })
            
        except ValidationError as e:
            return ErrorResult(
                message=str(e),
                code="VALIDATION_ERROR"
            )
        except CommandError as e:
            return ErrorResult(
                message=str(e),
                code="REMOVE_ERROR"
            )
        except Exception as e:
            return ErrorResult(
                message=f"Unexpected error during Docker rmi: {str(e)}",
                code="INTERNAL_ERROR"
            )
    
    @classmethod
    def get_schema(cls) -> Dict[str, Any]:
        """Get JSON schema for Docker remove command parameters."""
        return {
            "type": "object",
            "properties": {
                "images": {
                    "type": "array",
                    "description": "List of image names, IDs, or tags to remove",
                    "items": {"type": "string"},
                    "minItems": 1,
                    "examples": [
                        ["myapp:latest"],
                        ["nginx:alpine", "ubuntu:20.04"],
                        ["sha256:abc123..."]
                    ]
                },
                "force": {
                    "type": "boolean",
                    "description": "Force removal of the image",
                    "default": False
                },
                "no_prune": {
                    "type": "boolean",
                    "description": "Do not delete untagged parents",
                    "default": False
                }
            },
            "required": ["images"],
            "additionalProperties": False
        } 