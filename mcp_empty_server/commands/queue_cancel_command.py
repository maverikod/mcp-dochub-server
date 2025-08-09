"""Queue cancel command for cancelling tasks in queue."""

from typing import Dict, Any
from datetime import datetime
from mcp_proxy_adapter.commands.base import Command
from mcp_proxy_adapter.commands.result import SuccessResult, ErrorResult
from mcp_proxy_adapter.core.errors import ValidationError
from mcp_empty_server.queue.queue_manager import queue_manager


class QueueCancelCommand(Command):
    """Cancel Docker task in queue.
    
    This command cancels a pending or running Docker task in the queue.
    """
    
    name = "queue_cancel"
    
    async def execute(
        self,
        task_id: str,
        **kwargs
    ) -> SuccessResult:
        """Execute queue cancel command.
        
        Args:
            task_id: Task identifier to cancel
            
        Returns:
            Success result with cancellation status
        """
        try:
            # Validate inputs
            if not task_id:
                raise ValidationError("Task ID is required")
            
            # Cancel task
            cancelled = await queue_manager.cancel_task(task_id)
            
            if cancelled:
                return SuccessResult(data={
                    "status": "success",
                    "message": "Task cancelled successfully",
                    "task_id": task_id,
                    "cancelled": True,
                    "timestamp": datetime.now().isoformat()
                })
            else:
                return SuccessResult(data={
                    "status": "warning",
                    "message": "Task could not be cancelled (may not exist or already completed)",
                    "task_id": task_id,
                    "cancelled": False,
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
                message=f"Error cancelling task: {str(e)}",
                code="CANCEL_ERROR",
                details={"error_type": "unexpected", "error": str(e)}
            )
    
    @classmethod
    def get_schema(cls) -> Dict[str, Any]:
        """Get JSON schema for queue cancel command parameters."""
        return {
            "type": "object",
            "properties": {
                "task_id": {
                    "type": "string",
                    "description": "Task identifier (UUID) to cancel",
                    "minLength": 1,
                    "examples": ["123e4567-e89b-12d3-a456-426614174000"]
                }
            },
            "required": ["task_id"],
            "additionalProperties": False
        } 