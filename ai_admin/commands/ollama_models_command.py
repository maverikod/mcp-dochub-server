import subprocess
import json
import asyncio
from typing import Optional, Dict, Any, List
from datetime import datetime
from mcp_proxy_adapter.commands.base import Command
from mcp_proxy_adapter.commands.result import SuccessResult, ErrorResult
from ai_admin.queue.queue_manager import queue_manager
from ai_admin.commands.ollama_base import ollama_config
import os

class OllamaModelsCommand(Command):
    """Manage Ollama models - list, pull, remove, run models."""
    
    name = "ollama_models"
    
    async def execute(self, 
                     action: str = "list",
                     model_name: Optional[str] = None,
                     prompt: Optional[str] = None,
                     **kwargs):
        """Execute Ollama models command.
        
        Args:
            action: Action to perform (list, pull, remove, run, info)
            model_name: Name of the model for pull/remove/run actions
            prompt: Prompt for run action
            
        Returns:
            Success or error result
        """
        try:
            if action == "list":
                return await self._list_models()
            elif action == "pull" and model_name:
                return await self._pull_model_queued(model_name)
            elif action == "remove" and model_name:
                return await self._remove_model(model_name)
            elif action == "run" and model_name and prompt:
                return await self._run_model(model_name, prompt)
            elif action == "info" and model_name:
                return await self._model_info(model_name)
            else:
                return ErrorResult(
                    message="Invalid action or missing parameters",
                    code="INVALID_ACTION",
                    details={
                        "valid_actions": ["list", "pull", "remove", "run", "info"],
                        "required_params": {
                            "pull": ["model_name"],
                            "remove": ["model_name"], 
                            "run": ["model_name", "prompt"],
                            "info": ["model_name"]
                        }
                    }
                )
                
        except Exception as e:
            return ErrorResult(
                message=f"Ollama command failed: {str(e)}",
                code="OLLAMA_ERROR",
                details={"action": action, "model_name": model_name}
            )
    
    async def _list_models(self) -> SuccessResult:
        """List all available Ollama models."""
        try:
            # Set OLLAMA_MODELS environment variable for this command
            env = os.environ.copy()
            env['OLLAMA_MODELS'] = ollama_config.get_models_cache_path()
            
            result = subprocess.run(
                ["ollama", "list"],
                capture_output=True,
                text=True,
                timeout=ollama_config.get_ollama_timeout(),
                env=env
            )
            
            if result.returncode != 0:
                return ErrorResult(
                    message=f"Failed to list models: {result.stderr}",
                    code="OLLAMA_LIST_FAILED",
                    details={"stderr": result.stderr}
                )
            
            # Parse the output manually since --json is not supported
            output_lines = result.stdout.strip().split('\n')
            models = []
            
            # Skip header line and parse each model line
            for line in output_lines[1:]:  # Skip "NAME" header
                if line.strip():
                    parts = line.split()
                    if len(parts) >= 2:
                        model_info = {
                            "name": parts[0],
                            "size": parts[1] if len(parts) > 1 else "unknown",
                            "modified": parts[2] if len(parts) > 2 else "unknown"
                        }
                        models.append(model_info)
            
            return SuccessResult(data={
                "message": f"Found {len(models)} Ollama models",
                "models": models,
                "count": len(models),
                "raw_output": result.stdout,
                "cache_path": ollama_config.get_models_cache_path(),
                "timestamp": datetime.now().isoformat()
            })
            
        except subprocess.TimeoutExpired:
            return ErrorResult(
                message="Ollama list command timed out",
                code="TIMEOUT",
                details={"timeout": ollama_config.get_ollama_timeout()}
            )
    
    async def _pull_model(self, model_name: str) -> SuccessResult:
        """Pull/download an Ollama model."""
        try:
            # Set OLLAMA_MODELS environment variable for this command
            env = os.environ.copy()
            env['OLLAMA_MODELS'] = ollama_config.get_models_cache_path()
            
            # Start pull process
            process = subprocess.Popen(
                ["ollama", "pull", model_name],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                universal_newlines=True,
                env=env
            )
            
            # Collect output in real-time
            output_lines = []
            while True:
                output = process.stdout.readline()
                if output == '' and process.poll() is not None:
                    break
                if output:
                    output_lines.append(output.strip())
            
            # Check if process completed successfully
            return_code = process.poll()
            if return_code != 0:
                stderr = process.stderr.read()
                return ErrorResult(
                    message=f"Failed to pull model {model_name}",
                    code="OLLAMA_PULL_FAILED",
                    details={"model_name": model_name, "stderr": stderr, "return_code": return_code}
                )
            
            return SuccessResult(data={
                "message": f"Successfully pulled model {model_name}",
                "model_name": model_name,
                "output": output_lines,
                "timestamp": datetime.now().isoformat()
            })
            
        except Exception as e:
            return ErrorResult(
                message=f"Error pulling model {model_name}: {str(e)}",
                code="OLLAMA_PULL_ERROR",
                details={"model_name": model_name}
            )
    
    async def _remove_model(self, model_name: str) -> SuccessResult:
        """Remove an Ollama model."""
        try:
            # Set OLLAMA_MODELS environment variable for this command
            env = os.environ.copy()
            env['OLLAMA_MODELS'] = ollama_config.get_models_cache_path()
            
            result = subprocess.run(
                ["ollama", "rm", model_name],
                capture_output=True,
                text=True,
                timeout=ollama_config.get_ollama_timeout(),
                env=env
            )
            
            if result.returncode != 0:
                return ErrorResult(
                    message=f"Failed to remove model {model_name}: {result.stderr}",
                    code="OLLAMA_REMOVE_FAILED",
                    details={"model_name": model_name, "stderr": result.stderr}
                )
            
            return SuccessResult(data={
                "message": f"Successfully removed model {model_name}",
                "model_name": model_name,
                "output": result.stdout,
                "timestamp": datetime.now().isoformat()
            })
            
        except subprocess.TimeoutExpired:
            return ErrorResult(
                message=f"Removing model {model_name} timed out",
                code="TIMEOUT",
                details={"model_name": model_name, "timeout": 60}
            )
    
    async def _run_model(self, model_name: str, prompt: str) -> SuccessResult:
        """Run inference with an Ollama model."""
        try:
            # Prepare request data
            request_data = {
                "model": model_name,
                "prompt": prompt,
                "stream": False
            }
            
            # Use curl to make request to Ollama API
            curl_cmd = [
                "curl", "-s", "-X", "POST",
                f"{ollama_config.get_ollama_url()}/api/generate",
                "-H", "Content-Type: application/json",
                "-d", json.dumps(request_data)
            ]
            
            result = subprocess.run(
                curl_cmd,
                capture_output=True,
                text=True,
                timeout=120
            )
            
            if result.returncode != 0:
                return ErrorResult(
                    message=f"Failed to run model {model_name}",
                    code="OLLAMA_RUN_FAILED",
                    details={"model_name": model_name, "stderr": result.stderr}
                )
            
            try:
                response_data = json.loads(result.stdout)
                generated_text = response_data.get("response", "")
                
                return SuccessResult(data={
                    "message": f"Inference completed with model {model_name}",
                    "model_name": model_name,
                    "prompt": prompt,
                    "generated_text": generated_text,
                    "response_data": response_data,
                    "timestamp": datetime.now().isoformat()
                })
                
            except json.JSONDecodeError:
                return ErrorResult(
                    message=f"Invalid JSON response from Ollama",
                    code="INVALID_RESPONSE",
                    details={"model_name": model_name, "raw_response": result.stdout}
                )
            
        except subprocess.TimeoutExpired:
            return ErrorResult(
                message=f"Running model {model_name} timed out",
                code="TIMEOUT",
                details={"model_name": model_name, "timeout": 120}
            )
    
    async def _model_info(self, model_name: str) -> SuccessResult:
        """Get information about a specific model."""
        try:
            result = subprocess.run(
                ["ollama", "show", model_name, "--json"],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                return ErrorResult(
                    message=f"Failed to get info for model {model_name}: {result.stderr}",
                    code="OLLAMA_INFO_FAILED",
                    details={"model_name": model_name, "stderr": result.stderr}
                )
            
            model_info = json.loads(result.stdout) if result.stdout.strip() else {}
            
            return SuccessResult(data={
                "message": f"Model info for {model_name}",
                "model_name": model_name,
                "info": model_info,
                "timestamp": datetime.now().isoformat()
            })
            
        except subprocess.TimeoutExpired:
            return ErrorResult(
                message=f"Getting info for model {model_name} timed out",
                code="TIMEOUT",
                details={"model_name": model_name, "timeout": 30}
            )
    
    async def _pull_model_queued(self, model_name: str) -> SuccessResult:
        """Pull/download an Ollama model using task queue."""
        try:
            # Add task to queue
            task_id = await queue_manager.add_ollama_pull_task(model_name)
            
            return SuccessResult(data={
                "message": f"Ollama model pull task added to queue",
                "model_name": model_name,
                "task_id": task_id,
                "status": "queued",
                "note": "Use queue_task_status command to check progress",
                "timestamp": datetime.now().isoformat()
            })
            
        except Exception as e:
            return ErrorResult(
                message=f"Failed to add pull task to queue: {str(e)}",
                code="QUEUE_ERROR",
                details={"model_name": model_name}
            )
    
    @classmethod
    def get_schema(cls) -> Dict[str, Any]:
        """Get command schema."""
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "description": "Action to perform",
                    "enum": ["list", "pull", "remove", "run", "info"],
                    "default": "list"
                },
                "model_name": {
                    "type": "string",
                    "description": "Name of the model (required for pull/remove/run/info actions)",
                    "default": None
                },
                "prompt": {
                    "type": "string", 
                    "description": "Prompt for run action (required for run action)",
                    "default": None
                }
            },
            "required": ["action"],
            "additionalProperties": False
        } 