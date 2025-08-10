import subprocess
import json
import asyncio
from typing import Optional, Dict, Any
from datetime import datetime
from mcp_proxy_adapter.commands.base import Command
from mcp_proxy_adapter.commands.result import SuccessResult, ErrorResult
from ai_admin.queue.queue_manager import queue_manager
from ai_admin.commands.ollama_base import ollama_config

class OllamaRunCommand(Command):
    """Run Ollama model inference."""
    
    name = "ollama_run"
    
    async def execute(self, 
                     model_name: str,
                     prompt: str,
                     max_tokens: int = 1000,
                     temperature: float = 0.7,
                     use_queue: bool = False,
                     **kwargs):
        """Execute Ollama model inference.
        
        Args:
            model_name: Name of the model to use
            prompt: Input prompt
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            use_queue: Use task queue for long operations
            
        Returns:
            Success or error result
        """
        try:
            if use_queue:
                return await self._run_model_queued(model_name, prompt, max_tokens, temperature)
            else:
                return await self._run_model_direct(model_name, prompt, max_tokens, temperature)
                
        except Exception as e:
            return ErrorResult(
                message=f"Ollama run command failed: {str(e)}",
                code="OLLAMA_RUN_ERROR",
                details={"model_name": model_name, "error": str(e)}
            )
    
    async def _run_model_direct(self, model_name: str, prompt: str, max_tokens: int, temperature: float) -> SuccessResult:
        """Run model inference directly."""
        try:
            # Prepare request data
            request_data = {
                "model": model_name,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "num_predict": max_tokens,
                    "temperature": temperature
                }
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
                timeout=ollama_config.get_ollama_timeout()
            )
            
            if result.returncode != 0:
                return ErrorResult(
                    message=f"Ollama API request failed: {result.stderr}",
                    code="API_REQUEST_FAILED",
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
                    "prompt_tokens": response_data.get("prompt_eval_count", 0),
                    "generated_tokens": response_data.get("eval_count", 0),
                    "total_duration": response_data.get("eval_duration", 0),
                    "tokens_per_second": response_data.get("eval_count", 0) / (response_data.get("eval_duration", 1) / 1e9),
                    "timestamp": datetime.now().isoformat()
                })
                
            except json.JSONDecodeError as e:
                return ErrorResult(
                    message=f"Invalid JSON response from Ollama: {str(e)}",
                    code="INVALID_RESPONSE",
                    details={"model_name": model_name, "raw_response": result.stdout}
                )
                
        except subprocess.TimeoutExpired:
            return ErrorResult(
                message=f"Ollama inference timed out after {ollama_config.get_ollama_timeout()} seconds",
                code="TIMEOUT",
                details={"model_name": model_name, "timeout": ollama_config.get_ollama_timeout()}
            )
    
    async def _run_model_queued(self, model_name: str, prompt: str, max_tokens: int, temperature: float) -> SuccessResult:
        """Run model inference using task queue."""
        try:
            task_id = await queue_manager.add_ollama_run_task(
                model_name=model_name,
                prompt=prompt,
                max_tokens=max_tokens,
                temperature=temperature
            )
            
            return SuccessResult(data={
                "message": f"Ollama inference task queued for model {model_name}",
                "task_id": task_id,
                "model_name": model_name,
                "status": "queued",
                "timestamp": datetime.now().isoformat()
            })
            
        except Exception as e:
            return ErrorResult(
                message=f"Failed to queue Ollama inference task: {str(e)}",
                code="QUEUE_FAILED",
                details={"model_name": model_name, "error": str(e)}
            )
    
    @classmethod
    def get_schema(cls) -> Dict[str, Any]:
        """Get command schema."""
        return {
            "type": "object",
            "properties": {
                "model_name": {
                    "type": "string",
                    "description": "Name of the Ollama model to use",
                    "default": None
                },
                "prompt": {
                    "type": "string",
                    "description": "Input prompt for the model",
                    "default": None
                },
                "max_tokens": {
                    "type": "integer",
                    "description": "Maximum tokens to generate",
                    "default": 1000
                },
                "temperature": {
                    "type": "number",
                    "description": "Sampling temperature (0.0 to 1.0)",
                    "default": 0.7
                },
                "use_queue": {
                    "type": "boolean",
                    "description": "Use task queue for long operations",
                    "default": False
                }
            },
            "required": ["model_name", "prompt"],
            "additionalProperties": False
        } 