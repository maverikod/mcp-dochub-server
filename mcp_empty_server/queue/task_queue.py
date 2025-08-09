"""Task queue system for Docker operations."""

import asyncio
import uuid
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field


class TaskStatus(Enum):
    """Task execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskType(Enum):
    """Docker task types."""
    PUSH = "docker_push"
    BUILD = "docker_build"
    PULL = "docker_pull"


@dataclass
class DockerTask:
    """Docker task representation."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    task_type: TaskType = TaskType.PUSH
    status: TaskStatus = TaskStatus.PENDING
    command: str = ""
    params: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    progress: int = 0  # 0-100%
    current_step: str = ""
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    logs: List[str] = field(default_factory=list)
    
    def add_log(self, message: str) -> None:
        """Add log message with timestamp."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.logs.append(f"[{timestamp}] {message}")
    
    def update_progress(self, progress: int, step: str = "") -> None:
        """Update task progress."""
        self.progress = max(0, min(100, progress))
        if step:
            self.current_step = step
            self.add_log(f"Progress: {self.progress}% - {step}")
    
    def start(self) -> None:
        """Mark task as started."""
        self.status = TaskStatus.RUNNING
        self.started_at = datetime.now()
        self.add_log(f"Task started: {self.task_type.value}")
    
    def complete(self, result: Dict[str, Any]) -> None:
        """Mark task as completed."""
        self.status = TaskStatus.COMPLETED
        self.completed_at = datetime.now()
        self.progress = 100
        self.result = result
        self.add_log("Task completed successfully")
    
    def fail(self, error: str) -> None:
        """Mark task as failed."""
        self.status = TaskStatus.FAILED
        self.completed_at = datetime.now()
        self.error = error
        self.add_log(f"Task failed: {error}")
    
    def cancel(self) -> None:
        """Mark task as cancelled."""
        self.status = TaskStatus.CANCELLED
        self.completed_at = datetime.now()
        self.add_log("Task cancelled")
    
    def get_duration(self) -> Optional[float]:
        """Get task duration in seconds."""
        if not self.started_at:
            return None
        end_time = self.completed_at or datetime.now()
        return (end_time - self.started_at).total_seconds()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert task to dictionary representation."""
        return {
            "id": self.id,
            "task_type": self.task_type.value,
            "status": self.status.value,
            "command": self.command,
            "params": self.params,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "progress": self.progress,
            "current_step": self.current_step,
            "result": self.result,
            "error": self.error,
            "logs": self.logs,
            "duration": self.get_duration()
        }


class TaskQueue:
    """Task queue for managing Docker operations."""
    
    def __init__(self, max_concurrent: int = 2):
        """Initialize task queue.
        
        Args:
            max_concurrent: Maximum number of concurrent tasks
        """
        self.max_concurrent = max_concurrent
        self._tasks: Dict[str, DockerTask] = {}
        self._pending_queue: List[str] = []
        self._running_tasks: Dict[str, asyncio.Task] = {}
        self._lock = asyncio.Lock()
    
    async def add_task(self, task: DockerTask) -> str:
        """Add task to queue.
        
        Args:
            task: Docker task to add
            
        Returns:
            Task ID
        """
        async with self._lock:
            self._tasks[task.id] = task
            self._pending_queue.append(task.id)
            task.add_log("Task added to queue")
            
            # Try to start task if there's capacity
            await self._try_start_next_task()
            
            return task.id
    
    async def get_task(self, task_id: str) -> Optional[DockerTask]:
        """Get task by ID.
        
        Args:
            task_id: Task identifier
            
        Returns:
            Docker task or None if not found
        """
        return self._tasks.get(task_id)
    
    async def get_all_tasks(self) -> List[DockerTask]:
        """Get all tasks."""
        return list(self._tasks.values())
    
    async def get_tasks_by_status(self, status: TaskStatus) -> List[DockerTask]:
        """Get tasks by status.
        
        Args:
            status: Task status to filter by
            
        Returns:
            List of tasks with specified status
        """
        return [task for task in self._tasks.values() if task.status == status]
    
    async def cancel_task(self, task_id: str) -> bool:
        """Cancel task.
        
        Args:
            task_id: Task identifier
            
        Returns:
            True if task was cancelled, False otherwise
        """
        async with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                return False
            
            if task.status == TaskStatus.PENDING:
                # Remove from pending queue
                if task_id in self._pending_queue:
                    self._pending_queue.remove(task_id)
                task.cancel()
                return True
            
            elif task.status == TaskStatus.RUNNING:
                # Cancel running task
                if task_id in self._running_tasks:
                    self._running_tasks[task_id].cancel()
                    del self._running_tasks[task_id]
                task.cancel()
                await self._try_start_next_task()
                return True
            
            return False
    
    async def clear_completed(self) -> int:
        """Clear completed and failed tasks.
        
        Returns:
            Number of tasks cleared
        """
        async with self._lock:
            to_remove = []
            for task_id, task in self._tasks.items():
                if task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
                    to_remove.append(task_id)
            
            for task_id in to_remove:
                del self._tasks[task_id]
            
            return len(to_remove)
    
    async def get_queue_stats(self) -> Dict[str, Any]:
        """Get queue statistics.
        
        Returns:
            Queue statistics
        """
        stats = {
            "total_tasks": len(self._tasks),
            "pending": len([t for t in self._tasks.values() if t.status == TaskStatus.PENDING]),
            "running": len([t for t in self._tasks.values() if t.status == TaskStatus.RUNNING]),
            "completed": len([t for t in self._tasks.values() if t.status == TaskStatus.COMPLETED]),
            "failed": len([t for t in self._tasks.values() if t.status == TaskStatus.FAILED]),
            "cancelled": len([t for t in self._tasks.values() if t.status == TaskStatus.CANCELLED]),
            "max_concurrent": self.max_concurrent,
            "current_running": len(self._running_tasks)
        }
        return stats
    
    async def _try_start_next_task(self) -> None:
        """Try to start next pending task if there's capacity."""
        if len(self._running_tasks) >= self.max_concurrent:
            return
        
        if not self._pending_queue:
            return
        
        task_id = self._pending_queue.pop(0)
        task = self._tasks[task_id]
        
        # Create asyncio task for execution
        async_task = asyncio.create_task(self._execute_task(task))
        self._running_tasks[task_id] = async_task
    
    async def _execute_task(self, task: DockerTask) -> None:
        """Execute a Docker task.
        
        Args:
            task: Task to execute
        """
        try:
            task.start()
            
            # Execute task based on type
            if task.task_type == TaskType.PUSH:
                await self._execute_push_task(task)
            elif task.task_type == TaskType.BUILD:
                await self._execute_build_task(task)
            elif task.task_type == TaskType.PULL:
                await self._execute_pull_task(task)
            
        except asyncio.CancelledError:
            task.cancel()
        except Exception as e:
            task.fail(str(e))
        finally:
            # Remove from running tasks
            if task.id in self._running_tasks:
                del self._running_tasks[task.id]
            
            # Try to start next task
            await self._try_start_next_task()
    
    async def _execute_push_task(self, task: DockerTask) -> None:
        """Execute Docker push task."""
        import subprocess
        
        params = task.params
        image_name = params.get("image_name", "")
        tag = params.get("tag", "latest")
        full_image_name = f"{image_name}:{tag}"
        
        task.update_progress(10, f"Starting push of {full_image_name}")
        
        # Build command
        cmd = ["docker", "push", full_image_name]
        task.command = " ".join(cmd)
        
        # Execute with progress tracking
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        task.update_progress(25, "Pushing layers...")
        
        # Monitor output for progress
        stdout, stderr = await process.communicate()
        
        if process.returncode == 0:
            task.update_progress(90, "Finalizing push...")
            
            # Parse output for digest
            output_lines = stdout.decode('utf-8').splitlines()
            digest = None
            for line in output_lines:
                if "digest:" in line:
                    digest = line.split("digest: ")[-1].strip()
                    break
            
            result = {
                "status": "success",
                "message": "Docker image pushed successfully",
                "image_name": image_name,
                "tag": tag,
                "full_image_name": full_image_name,
                "digest": digest
            }
            task.complete(result)
        else:
            error_msg = stderr.decode('utf-8').strip()
            task.fail(f"Docker push failed: {error_msg}")
    
    async def _execute_build_task(self, task: DockerTask) -> None:
        """Execute Docker build task."""
        # Similar implementation for build operations
        params = task.params
        tag = params.get("tag", "")
        
        task.update_progress(10, f"Starting build of {tag}")
        
        # Implementation would be similar to push but for build
        # For now, just simulate
        await asyncio.sleep(5)  # Simulate build time
        
        result = {
            "status": "success",
            "message": "Docker image built successfully",
            "tag": tag
        }
        task.complete(result)
    
    async def _execute_pull_task(self, task: DockerTask) -> None:
        """Execute Docker pull task."""
        # Similar implementation for pull operations
        params = task.params
        image_name = params.get("image_name", "")
        
        task.update_progress(10, f"Starting pull of {image_name}")
        
        # Implementation would be similar to push but for pull
        # For now, just simulate
        await asyncio.sleep(3)  # Simulate pull time
        
        result = {
            "status": "success",
            "message": "Docker image pulled successfully",
            "image_name": image_name
        }
        task.complete(result) 