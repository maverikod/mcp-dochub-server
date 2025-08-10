import subprocess
import json
import requests
from typing import Optional, Dict, Any, List
from datetime import datetime
from mcp_proxy_adapter.commands.base import Command
from mcp_proxy_adapter.commands.result import SuccessResult, ErrorResult

class LLMInferenceCommand(Command):
    """Execute LLM inference on local or cloud models."""
    
    name = "llm_inference"
    
    async def execute(self, 
                     prompt: str,
                     model: str = "llama2:7b",
                     backend: str = "local",  # local, vast, openai
                     max_tokens: int = 1000,
                     temperature: float = 0.7,
                     vast_instance_id: Optional[str] = None,
                     **kwargs):
        """Execute LLM inference.
        
        Args:
            prompt: Input prompt for the model
            model: Model name (e.g., llama2:7b, gpt-4)
            backend: Backend to use (local, vast, openai)
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (0.0-2.0)
            vast_instance_id: Vast.ai instance ID for cloud inference
            
        Returns:
            Success or error result with generated text
        """
        try:
            if backend == "local":
                return await self._local_inference(prompt, model, max_tokens, temperature)
            elif backend == "vast":
                return await self._vast_inference(prompt, model, max_tokens, temperature, vast_instance_id)
            elif backend == "openai":
                return await self._openai_inference(prompt, model, max_tokens, temperature)
            else:
                return ErrorResult(
                    message=f"Unsupported backend: {backend}",
                    code="UNSUPPORTED_BACKEND",
                    details={"supported_backends": ["local", "vast", "openai"]}
                )
                
        except Exception as e:
            return ErrorResult(
                message=f"LLM inference failed: {str(e)}",
                code="INFERENCE_ERROR",
                details={"backend": backend, "model": model}
            )
    
    async def _local_inference(self, prompt: str, model: str, max_tokens: int, temperature: float) -> SuccessResult:
        """Execute inference on local Ollama model."""
        try:
            # Prepare Ollama request
            request_data = {
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "num_predict": max_tokens,
                    "temperature": temperature
                }
            }
            
            # Send request to Ollama
            response = requests.post(
                "http://localhost:11434/api/generate",
                json=request_data,
                timeout=120
            )
            
            if response.status_code != 200:
                return ErrorResult(
                    message=f"Ollama request failed: {response.text}",
                    code="OLLAMA_REQUEST_FAILED",
                    details={"status_code": response.status_code}
                )
            
            result = response.json()
            
            return SuccessResult(data={
                "message": "Local inference completed",
                "model": model,
                "backend": "local",
                "generated_text": result.get("response", ""),
                "prompt_tokens": result.get("prompt_eval_count", 0),
                "generated_tokens": result.get("eval_count", 0),
                "total_duration": result.get("eval_duration", 0),
                "tokens_per_second": result.get("eval_count", 0) / (result.get("eval_duration", 1) / 1e9),
                "timestamp": datetime.now().isoformat()
            })
            
        except requests.exceptions.RequestException as e:
            return ErrorResult(
                message=f"Failed to connect to Ollama: {str(e)}",
                code="OLLAMA_CONNECTION_FAILED",
                details={"model": model}
            )
    
    async def _vast_inference(self, prompt: str, model: str, max_tokens: int, temperature: float, instance_id: Optional[str]) -> SuccessResult:
        """Execute inference on Vast.ai instance."""
        try:
            if not instance_id:
                return ErrorResult(
                    message="Vast.ai instance ID is required for cloud inference",
                    code="MISSING_INSTANCE_ID",
                    details={"backend": "vast"}
                )
            
            # This would connect to the Vast.ai instance and run inference
            # Implementation depends on how the Vast.ai instance is set up
            
            # For now, return a placeholder
            return SuccessResult(data={
                "message": "Vast.ai inference (placeholder)",
                "model": model,
                "backend": "vast",
                "instance_id": instance_id,
                "generated_text": f"[Vast.ai inference for: {prompt[:50]}...]",
                "note": "Implementation requires Vast.ai instance setup with Ollama",
                "timestamp": datetime.now().isoformat()
            })
            
        except Exception as e:
            return ErrorResult(
                message=f"Vast.ai inference failed: {str(e)}",
                code="VAST_INFERENCE_FAILED",
                details={"instance_id": instance_id, "model": model}
            )
    
    async def _openai_inference(self, prompt: str, model: str, max_tokens: int, temperature: float) -> SuccessResult:
        """Execute inference using OpenAI API."""
        try:
            # This would use OpenAI API
            # Implementation requires OpenAI API key configuration
            
            return SuccessResult(data={
                "message": "OpenAI inference (placeholder)",
                "model": model,
                "backend": "openai",
                "generated_text": f"[OpenAI inference for: {prompt[:50]}...]",
                "note": "Implementation requires OpenAI API key configuration",
                "timestamp": datetime.now().isoformat()
            })
            
        except Exception as e:
            return ErrorResult(
                message=f"OpenAI inference failed: {str(e)}",
                code="OPENAI_INFERENCE_FAILED",
                details={"model": model}
            )
    
    @classmethod
    def get_schema(cls) -> Dict[str, Any]:
        """Get command schema."""
        return {
            "type": "object",
            "properties": {
                "prompt": {
                    "type": "string",
                    "description": "Input prompt for the model",
                    "minLength": 1
                },
                "model": {
                    "type": "string",
                    "description": "Model name (e.g., llama2:7b, gpt-4)",
                    "default": "llama2:7b"
                },
                "backend": {
                    "type": "string",
                    "description": "Backend to use",
                    "enum": ["local", "vast", "openai"],
                    "default": "local"
                },
                "max_tokens": {
                    "type": "integer",
                    "description": "Maximum tokens to generate",
                    "minimum": 1,
                    "maximum": 10000,
                    "default": 1000
                },
                "temperature": {
                    "type": "number",
                    "description": "Sampling temperature (0.0-2.0)",
                    "minimum": 0.0,
                    "maximum": 2.0,
                    "default": 0.7
                },
                "vast_instance_id": {
                    "type": "string",
                    "description": "Vast.ai instance ID for cloud inference",
                    "default": None
                }
            },
            "required": ["prompt"],
            "additionalProperties": False
        } 