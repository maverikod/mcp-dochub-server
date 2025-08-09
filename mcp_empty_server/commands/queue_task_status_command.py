"""Queue task status command for monitoring individual tasks."""

from typing import Dict, Any, Optional
from datetime import datetime
from mcp_proxy_adapter.commands.base import Command
from mcp_proxy_adapter.commands.result import SuccessResult, ErrorResult
from mcp_proxy_adapter.core.errors import ValidationError
from mcp_empty_server.queue.queue_manager import queue_manager


class QueueTaskStatusCommand(Command):
    """Get status of individual Docker task in queue.
    
    This command provides detailed information about a specific task
    including progress, logs, and current status.
    """
    
    name = "queue_task_status"
    
    async def execute(
        self,
        task_id: str,
        include_logs: bool = True,
        **kwargs
    ) -> SuccessResult:
        """Execute queue task status command.
        
        Args:
            task_id: Task identifier
            include_logs: Include task logs in response
            
        Returns:
            Success result with task status
        """
        try:
            # Validate inputs
            if not task_id:
                raise ValidationError("Task ID is required")
            
            # Get task status
            task_status = await queue_manager.get_task_status(task_id)
            
            if not task_status:
                return ErrorResult(
                    message=f"Task with ID '{task_id}' not found",
                    code="TASK_NOT_FOUND",
                    details={"task_id": task_id}
                )
            
            # Get task logs if requested
            logs = None
            if include_logs:
                logs = await queue_manager.get_task_logs(task_id)
            
            return SuccessResult(data={
                "status": "success",
                "message": "Task status retrieved successfully",
                "task": task_status,
                "logs": logs if include_logs else None,
                "timestamp": datetime.now().isoformat()
            })
            
        except ValidationError as e:
            return ErrorResult(
                message=str(e),
                code="VALIDATION_ERROR",
                details={"error_type": "validation"}
            )
        except Exception as e:
            return ErrorResult(
                message=f"Error getting task status: {str(e)}",
                code="TASK_STATUS_ERROR",
                details={"error_type": "unexpected", "error": str(e)}
            )
    
    @classmethod
    def get_schema(cls) -> Dict[str, Any]:
        """Get JSON schema for queue task status command parameters."""
        return {
            "type": "object",
            "properties": {
                "task_id": {
                    "type": "string",
                    "description": "Task identifier (UUID)",
                    "minLength": 1,
                    "examples": ["123e4567-e89b-12d3-a456-426614174000"]
                },
                "include_logs": {
                    "type": "boolean",
                    "description": "Include task logs in response",
                    "default": True
                }
            },
            "required": ["task_id"],
            "additionalProperties": False
        } 