"""Queue push command for adding Docker push tasks to queue."""

from typing import Dict, Any, Optional
from datetime import datetime
from mcp_proxy_adapter.commands.base import Command
from mcp_proxy_adapter.commands.result import SuccessResult, ErrorResult
from mcp_proxy_adapter.core.errors import ValidationError
from mcp_empty_server.queue.queue_manager import queue_manager


class QueuePushCommand(Command):
    """Add Docker push task to background queue.
    
    This command adds a Docker push operation to the background task queue,
    allowing large images to be pushed without blocking the API.
    """
    
    name = "queue_push"
    
    async def execute(
        self,
        image_name: str,
        tag: str = "latest",
        all_tags: bool = False,
        disable_content_trust: bool = False,
        quiet: bool = False,
        **kwargs
    ) -> SuccessResult:
        """Execute queue push command.
        
        Args:
            image_name: Name of the image to push (e.g., 'username/myapp')
            tag: Tag to push (default: 'latest')
            all_tags: Push all tags of the image
            disable_content_trust: Skip image signing
            quiet: Suppress verbose output
            
        Returns:
            Success result with task ID
        """
        try:
            # Validate inputs
            if not image_name:
                raise ValidationError("Image name is required")
            
            # Add task to queue
            task_id = await queue_manager.add_push_task(
                image_name=image_name,
                tag=tag,
                all_tags=all_tags,
                disable_content_trust=disable_content_trust,
                quiet=quiet
            )
            
            return SuccessResult(data={
                "status": "success",
                "message": "Docker push task added to queue",
                "task_id": task_id,
                "image_name": image_name,
                "tag": tag,
                "queue_position": "Task added to queue",
                "timestamp": datetime.now().isoformat(),
                "note": "Use 'queue_task_status' command to monitor progress"
            })
            
        except ValidationError as e:
            return ErrorResult(
                message=str(e),
                code="VALIDATION_ERROR",
                details={"error_type": "validation"}
            )
        except Exception as e:
            return ErrorResult(
                message=f"Error adding push task to queue: {str(e)}",
                code="QUEUE_ERROR",
                details={"error_type": "unexpected", "error": str(e)}
            )
    
    @classmethod
    def get_schema(cls) -> Dict[str, Any]:
        """Get JSON schema for queue push command parameters."""
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