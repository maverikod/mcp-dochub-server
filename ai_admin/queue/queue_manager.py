"""Queue manager for Docker operations."""

from typing import Dict, List, Any, Optional
from ai_admin.queue.task_queue import TaskQueue, DockerTask, TaskType, TaskStatus


class QueueManager:
    """Manager for Docker task queues."""
    
    _instance: Optional['QueueManager'] = None
    
    def __new__(cls) -> 'QueueManager':
        """Singleton pattern implementation."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Initialize queue manager."""
        if self._initialized:
            return
        
        self.task_queue = TaskQueue(max_concurrent=2)
        self._initialized = True
    
    async def add_push_task(
        self,
        image_name: str,
        tag: str = "latest",
        **options
    ) -> str:
        """Add Docker push task to queue.
        
        Args:
            image_name: Docker image name
            tag: Image tag
            **options: Additional push options
            
        Returns:
            Task ID
        """
        task = DockerTask(
            task_type=TaskType.PUSH,
            params={
                "image_name": image_name,
                "tag": tag,
                **options
            }
        )
        
        return await self.task_queue.add_task(task)
    
    async def add_build_task(
        self,
        dockerfile_path: str = "Dockerfile",
        tag: Optional[str] = None,
        context_path: str = ".",
        **options
    ) -> str:
        """Add Docker build task to queue.
        
        Args:
            dockerfile_path: Path to Dockerfile
            tag: Tag for built image
            context_path: Build context path
            **options: Additional build options
            
        Returns:
            Task ID
        """
        task = DockerTask(
            task_type=TaskType.BUILD,
            params={
                "dockerfile_path": dockerfile_path,
                "tag": tag,
                "context_path": context_path,
                **options
            }
        )
        
        return await self.task_queue.add_task(task)
    
    async def add_pull_task(
        self,
        image_name: str,
        tag: str = "latest",
        **options
    ) -> str:
        """Add Docker pull task to queue.
        
        Args:
            image_name: Docker image name
            tag: Image tag
            **options: Additional pull options
            
        Returns:
            Task ID
        """
        task = DockerTask(
            task_type=TaskType.PULL,
            params={
                "image_name": image_name,
                "tag": tag,
                **options
            }
        )
        
        return await self.task_queue.add_task(task)
    
    async def add_ollama_pull_task(
        self,
        model_name: str,
        **options
    ) -> str:
        """Add Ollama model pull task to queue.
        
        Args:
            model_name: Ollama model name
            **options: Additional pull options
            
        Returns:
            Task ID
        """
        task = DockerTask(
            task_type=TaskType.OLLAMA_PULL,
            params={
                "model_name": model_name,
                **options
            }
        )
        
        return await self.task_queue.add_task(task)
    
    async def add_ollama_run_task(
        self,
        model_name: str,
        prompt: str,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        **options
    ) -> str:
        """Add Ollama model inference task to queue.
        
        Args:
            model_name: Ollama model name
            prompt: Input prompt
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            **options: Additional inference options
            
        Returns:
            Task ID
        """
        task = DockerTask(
            task_type=TaskType.OLLAMA_RUN,
            params={
                "model_name": model_name,
                "prompt": prompt,
                "max_tokens": max_tokens,
                "temperature": temperature,
                **options
            }
        )
        
        return await self.task_queue.add_task(task)
    
    async def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get task status by ID.
        
        Args:
            task_id: Task identifier
            
        Returns:
            Task status dict or None if not found
        """
        task = await self.task_queue.get_task(task_id)
        return task.to_dict() if task else None
    
    async def get_all_tasks(self) -> List[Dict[str, Any]]:
        """Get all tasks.
        
        Returns:
            List of task dictionaries
        """
        tasks = await self.task_queue.get_all_tasks()
        return [task.to_dict() for task in tasks]
    
    async def get_queue_status(self) -> Dict[str, Any]:
        """Get queue status and statistics.
        
        Returns:
            Queue status information
        """
        stats = await self.task_queue.get_queue_stats()
        
        # Add recent tasks info
        recent_tasks = await self.task_queue.get_all_tasks()
        recent_tasks.sort(key=lambda t: t.created_at, reverse=True)
        
        return {
            "statistics": stats,
            "recent_tasks": [task.to_dict() for task in recent_tasks[:10]],
            "running_tasks": [
                task.to_dict() 
                for task in recent_tasks 
                if task.status == TaskStatus.RUNNING
            ]
        }
    
    async def cancel_task(self, task_id: str) -> bool:
        """Cancel task by ID.
        
        Args:
            task_id: Task identifier
            
        Returns:
            True if task was cancelled, False otherwise
        """
        return await self.task_queue.cancel_task(task_id)
    
    async def clear_completed_tasks(self) -> int:
        """Clear completed and failed tasks.
        
        Returns:
            Number of tasks cleared
        """
        return await self.task_queue.clear_completed()
    
    async def pause_queue(self) -> bool:
        """Pause task queue (stop processing new tasks).
        
        Returns:
            True if queue was paused
        """
        # Set max_concurrent to 0 to pause
        self.task_queue.max_concurrent = 0
        return True
    
    async def resume_queue(self, max_concurrent: int = 2) -> bool:
        """Resume task queue processing.
        
        Args:
            max_concurrent: Maximum concurrent tasks
            
        Returns:
            True if queue was resumed
        """
        self.task_queue.max_concurrent = max_concurrent
        # Try to start pending tasks
        await self.task_queue._try_start_next_task()
        return True
    
    async def get_task_logs(self, task_id: str) -> Optional[List[str]]:
        """Get task logs by ID.
        
        Args:
            task_id: Task identifier
            
        Returns:
            List of log messages or None if task not found
        """
        task = await self.task_queue.get_task(task_id)
        return task.logs if task else None


# Global queue manager instance
queue_manager = QueueManager() 