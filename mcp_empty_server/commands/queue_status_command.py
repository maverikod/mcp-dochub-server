"""Queue status command for monitoring Docker task queue."""

from typing import Dict, Any
from datetime import datetime
from mcp_proxy_adapter.commands.base import Command
from mcp_proxy_adapter.commands.result import SuccessResult, ErrorResult
from mcp_empty_server.queue.queue_manager import queue_manager


class QueueStatusCommand(Command):
    """Get status and statistics of Docker task queue.
    
    This command provides information about running, pending, completed,
    and failed Docker tasks in the queue.
    """
    
    name = "queue_status"
    
    async def execute(
        self,
        include_logs: bool = False,
        **kwargs
    ) -> SuccessResult:
        """Execute queue status command.
        
        Args:
            include_logs: Include task logs in response
            
        Returns:
            Success result with queue status
        """
        try:
            # Get queue status
            queue_status = await queue_manager.get_queue_status()
            
            # Get all tasks if logs requested
            if include_logs:
                all_tasks = await queue_manager.get_all_tasks()
                queue_status["all_tasks_with_logs"] = all_tasks
            
            return SuccessResult(data={
                "status": "success",
                "message": "Queue status retrieved successfully",
                "queue_status": queue_status,
                "timestamp": datetime.now().isoformat()
            })
            
        except Exception as e:
            return ErrorResult(
                message=f"Error getting queue status: {str(e)}",
                code="QUEUE_STATUS_ERROR",
                details={"error_type": "unexpected", "error": str(e)}
            )
    
    @classmethod
    def get_schema(cls) -> Dict[str, Any]:
        """Get JSON schema for queue status command parameters."""
        return {
            "type": "object",
            "properties": {
                "include_logs": {
                    "type": "boolean",
                    "description": "Include task logs in response",
                    "default": False
                }
            },
            "required": [],
            "additionalProperties": False
        } 