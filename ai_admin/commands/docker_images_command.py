"""Docker images command for listing container images."""

import asyncio
import json
from typing import Dict, Any, Optional, List
from datetime import datetime
from mcp_proxy_adapter.commands.base import Command
from mcp_proxy_adapter.commands.result import SuccessResult, ErrorResult
from mcp_proxy_adapter.core.errors import CommandError


class DockerImagesCommand(Command):
    """List Docker images on the local system.
    
    This command displays information about Docker images including
    repository, tag, image ID, creation time, and size.
    """
    
    name = "docker_images"
    
    async def execute(
        self,
        repository: Optional[str] = None,
        all_images: bool = False,
        quiet: bool = False,
        no_trunc: bool = False,
        format_output: str = "table",
        filter_dangling: Optional[bool] = None,
        **kwargs
    ) -> SuccessResult:
        """Execute Docker images command.
        
        Args:
            repository: Show images for specific repository
            all_images: Show all images (including intermediate layers)
            quiet: Only show image IDs
            no_trunc: Don't truncate output
            format_output: Output format (table, json)
            filter_dangling: Filter dangling images (True/False)
            
        Returns:
            Success result with images information
        """
        try:
            # Build Docker images command
            cmd = ["docker", "images"]
            
            # Add options
            if all_images:
                cmd.append("-a")
            
            if quiet:
                cmd.append("-q")
            
            if no_trunc:
                cmd.append("--no-trunc")
            
            # Add format for structured output
            if format_output == "json":
                cmd.extend(["--format", "json"])
            
            # Add filter for dangling images
            if filter_dangling is not None:
                if filter_dangling:
                    cmd.extend(["--filter", "dangling=true"])
                else:
                    cmd.extend(["--filter", "dangling=false"])
            
            # Add repository filter if specified
            if repository:
                cmd.append(repository)
            
            # Execute images command
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
                    f"Docker images command failed with exit code {process.returncode}",
                    data={
                        "stderr": error_output,
                        "command": " ".join(cmd),
                        "exit_code": process.returncode
                    }
                )
            
            # Parse output
            output = stdout.decode('utf-8').strip()
            
            if quiet:
                # For quiet mode, return list of image IDs
                image_ids = output.splitlines() if output else []
                return SuccessResult(data={
                    "format": "quiet",
                    "image_ids": image_ids,
                    "count": len(image_ids),
                    "timestamp": end_time.isoformat()
                })
            
            elif format_output == "json":
                # Parse JSON output
                images = []
                if output:
                    for line in output.splitlines():
                        try:
                            images.append(json.loads(line))
                        except json.JSONDecodeError:
                            continue
                
                return SuccessResult(data={
                    "format": "json",
                    "images": images,
                    "count": len(images),
                    "timestamp": end_time.isoformat()
                })
            
            else:
                # Parse table format
                lines = output.splitlines()
                if not lines:
                    return SuccessResult(data={
                        "format": "table",
                        "images": [],
                        "count": 0,
                        "timestamp": end_time.isoformat()
                    })
                
                # Skip header line
                header = lines[0] if lines else ""
                image_lines = lines[1:] if len(lines) > 1 else []
                
                images = []
                for line in image_lines:
                    if line.strip():
                        parts = line.split()
                        if len(parts) >= 5:
                            images.append({
                                "repository": parts[0],
                                "tag": parts[1],
                                "image_id": parts[2],
                                "created": " ".join(parts[3:-1]),
                                "size": parts[-1]
                            })
                
                return SuccessResult(data={
                    "format": "table",
                    "header": header,
                    "images": images,
                    "count": len(images),
                    "filters": {
                        "repository": repository,
                        "all_images": all_images,
                        "dangling": filter_dangling
                    },
                    "timestamp": end_time.isoformat()
                })
            
        except CommandError as e:
            return ErrorResult(
                message=str(e),
                code="IMAGES_ERROR"
            )
        except Exception as e:
            return ErrorResult(
                message=f"Unexpected error listing Docker images: {str(e)}",
                code="INTERNAL_ERROR"
            )
    
    @classmethod
    def get_schema(cls) -> Dict[str, Any]:
        """Get JSON schema for Docker images command parameters."""
        return {
            "type": "object",
            "properties": {
                "repository": {
                    "type": "string",
                    "description": "Show images for specific repository",
                    "examples": ["nginx", "ubuntu", "myusername/myapp"]
                },
                "all_images": {
                    "type": "boolean",
                    "description": "Show all images (including intermediate layers)",
                    "default": False
                },
                "quiet": {
                    "type": "boolean",
                    "description": "Only show image IDs",
                    "default": False
                },
                "no_trunc": {
                    "type": "boolean",
                    "description": "Don't truncate output",
                    "default": False
                },
                "format_output": {
                    "type": "string",
                    "description": "Output format",
                    "enum": ["table", "json"],
                    "default": "table"
                },
                "filter_dangling": {
                    "type": "boolean",
                    "description": "Filter dangling images (True for dangling only, False for non-dangling only)"
                }
            },
            "required": [],
            "additionalProperties": False
        } 