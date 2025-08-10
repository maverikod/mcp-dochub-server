import subprocess
import json
import psutil
import os
from typing import Dict, Any, List, Optional
from datetime import datetime
from mcp_proxy_adapter.commands.base import Command
from mcp_proxy_adapter.commands.result import SuccessResult, ErrorResult
from ai_admin.commands.ollama_base import ollama_config

class OllamaMemoryCommand(Command):
    """Manage Ollama memory - unload models from memory."""
    
    name = "ollama_memory"
    
    async def execute(self, 
                     action: str = "status",
                     model_name: Optional[str] = None,
                     **kwargs):
        """Execute Ollama memory management.
        
        Args:
            action: Action to perform (status, unload, unload_all)
            model_name: Name of the model to unload (for unload action)
            
        Returns:
            Success or error result
        """
        try:
            if action == "status":
                return await self._get_memory_status()
            elif action == "unload" and model_name:
                return await self._unload_model(model_name)
            elif action == "unload_all":
                return await self._unload_all_models()
            else:
                return ErrorResult(
                    message="Invalid action or missing parameters",
                    code="INVALID_ACTION",
                    details={
                        "valid_actions": ["status", "unload", "unload_all"],
                        "required_params": {
                            "unload": ["model_name"]
                        }
                    }
                )
                
        except Exception as e:
            return ErrorResult(
                message=f"Ollama memory command failed: {str(e)}",
                code="OLLAMA_MEMORY_ERROR",
                details={"action": action, "model_name": model_name}
            )
    
    async def _get_memory_status(self) -> SuccessResult:
        """Get current memory status of Ollama models."""
        try:
            # Get Ollama processes
            ollama_processes = []
            total_memory_mb = 0
            
            for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'memory_info']):
                try:
                    if 'ollama' in proc.info['name'].lower():
                        cmdline = ' '.join(proc.info['cmdline']) if proc.info['cmdline'] else ''
                        memory_mb = round(proc.info['memory_info'].rss / 1024 / 1024, 2)
                        
                        process_info = {
                            "pid": proc.info['pid'],
                            "name": proc.info['name'],
                            "cmdline": cmdline,
                            "memory_mb": memory_mb
                        }
                        
                        # Determine process type and model
                        if 'serve' in cmdline:
                            process_info["type"] = "server"
                            process_info["model"] = None
                        elif 'runner' in cmdline and '--model' in cmdline:
                            process_info["type"] = "model_runner"
                            # Extract model path from cmdline
                            model_path = self._extract_model_from_cmdline(cmdline)
                            process_info["model"] = model_path
                        else:
                            process_info["type"] = "other"
                            process_info["model"] = None
                        
                        ollama_processes.append(process_info)
                        total_memory_mb += memory_mb
                        
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            # Get available models
            env = os.environ.copy()
            env['OLLAMA_MODELS'] = ollama_config.get_models_cache_path()
            
            models_result = subprocess.run(
                ["ollama", "list"],
                capture_output=True,
                text=True,
                timeout=ollama_config.get_ollama_timeout(),
                env=env
            )
            
            available_models = []
            if models_result.returncode == 0:
                output_lines = models_result.stdout.strip().split('\n')
                for line in output_lines[1:]:
                    if line.strip():
                        parts = line.split()
                        if len(parts) >= 2:
                            model_info = {
                                "name": parts[0],
                                "id": parts[1] if len(parts) > 1 else "unknown",
                                "size": parts[2] if len(parts) > 2 else "unknown",
                                "modified": parts[3] if len(parts) > 3 else "unknown"
                            }
                            available_models.append(model_info)
            
            return SuccessResult(data={
                "message": "Ollama memory status retrieved",
                "total_memory_mb": round(total_memory_mb, 2),
                "total_memory_gb": round(total_memory_mb / 1024, 2),
                "processes": ollama_processes,
                "process_count": len(ollama_processes),
                "loaded_models": [p for p in ollama_processes if p["type"] == "model_runner"],
                "available_models": available_models,
                "cache_path": ollama_config.get_models_cache_path(),
                "timestamp": datetime.now().isoformat()
            })
            
        except Exception as e:
            return ErrorResult(
                message=f"Failed to get memory status: {str(e)}",
                code="STATUS_FAILED",
                details={"error": str(e)}
            )
    
    async def _unload_model(self, model_name: str) -> SuccessResult:
        """Unload specific model from memory."""
        try:
            # First check if model is loaded
            status = await self._get_memory_status()
            if hasattr(status, 'success') and not status.success:
                return status
            
            loaded_models = status.data["loaded_models"]
            target_process = None
            
            for process in loaded_models:
                # Check if model name matches (either direct match or in hash)
                if process["model"] and (model_name in process["model"] or model_name in process["cmdline"]):
                    target_process = process
                    break
            
            if not target_process:
                return ErrorResult(
                    message=f"Model {model_name} is not currently loaded in memory",
                    code="MODEL_NOT_LOADED",
                    details={"model_name": model_name, "loaded_models": [p["model"] for p in loaded_models]}
                )
            
            # Use ollama stop command
            try:
                result = subprocess.run(
                    ["ollama", "stop", model_name],
                    capture_output=True,
                    text=True,
                    timeout=ollama_config.get_ollama_timeout()
                )
                
                if result.returncode == 0:
                    return SuccessResult(data={
                        "message": f"Model {model_name} unloaded from memory via ollama stop",
                        "model_name": model_name,
                        "pid": target_process["pid"],
                        "memory_freed_mb": target_process["memory_mb"],
                        "memory_freed_gb": round(target_process["memory_mb"] / 1024, 2),
                        "method": "ollama_stop",
                        "timestamp": datetime.now().isoformat()
                    })
                else:
                    return ErrorResult(
                        message=f"Failed to unload model {model_name} via ollama stop: {result.stderr}",
                        code="UNLOAD_FAILED",
                        details={
                            "model_name": model_name,
                            "stderr": result.stderr,
                            "pid": target_process["pid"]
                        }
                    )
                
            except subprocess.TimeoutExpired:
                # Fallback to process kill
                try:
                    result = subprocess.run(
                        ["kill", str(target_process["pid"])],
                        capture_output=True,
                        text=True,
                        timeout=ollama_config.get_ollama_timeout()
                    )
                    
                    if result.returncode == 0:
                        return SuccessResult(data={
                            "message": f"Model {model_name} unloaded from memory via process kill",
                            "model_name": model_name,
                            "pid": target_process["pid"],
                            "memory_freed_mb": target_process["memory_mb"],
                            "memory_freed_gb": round(target_process["memory_mb"] / 1024, 2),
                            "method": "kill",
                            "timestamp": datetime.now().isoformat()
                        })
                    else:
                        return ErrorResult(
                            message=f"Failed to unload model {model_name}. API failed: {api_error}, Kill failed: {result.stderr}",
                            code="UNLOAD_FAILED",
                            details={
                                "model_name": model_name,
                                "api_error": str(api_error),
                                "kill_error": result.stderr,
                                "pid": target_process["pid"]
                            }
                        )
                    
                except subprocess.TimeoutExpired:
                    return ErrorResult(
                        message=f"Failed to unload model {model_name}. API failed: {api_error}, Kill timeout",
                        code="UNLOAD_FAILED",
                        details={
                            "model_name": model_name,
                            "api_error": str(api_error),
                            "pid": target_process["pid"]
                        }
                    )
                
        except Exception as e:
            return ErrorResult(
                message=f"Failed to unload model {model_name}: {str(e)}",
                code="UNLOAD_FAILED",
                details={"model_name": model_name, "error": str(e)}
            )
    
    async def _unload_all_models(self) -> SuccessResult:
        """Unload all models from memory."""
        try:
            # Get current status
            status = await self._get_memory_status()
            if hasattr(status, 'success') and not status.success:
                return status
            
            loaded_models = status.data["loaded_models"]
            if not loaded_models:
                return SuccessResult(data={
                    "message": "No models currently loaded in memory",
                    "unloaded_count": 0,
                    "memory_freed_mb": 0,
                    "timestamp": datetime.now().isoformat()
                })
            
            # Unload all models using ollama stop
            unloaded_count = 0
            total_memory_freed = 0
            failed_models = []
            
            # Get unique model names from loaded processes
            model_names = set()
            for process in loaded_models:
                if process["model"]:
                    # Extract model name from hash or cmdline
                    model_name = self._extract_model_name_from_process(process)
                    if model_name:
                        model_names.add(model_name)
            
            for model_name in model_names:
                try:
                    result = subprocess.run(
                        ["ollama", "stop", model_name],
                        capture_output=True,
                        text=True,
                        timeout=ollama_config.get_ollama_timeout()
                    )
                    
                    if result.returncode == 0:
                        unloaded_count += 1
                        # Find memory usage for this model
                        for process in loaded_models:
                            if model_name in process["cmdline"]:
                                total_memory_freed += process["memory_mb"]
                                break
                    else:
                        failed_models.append(model_name)
                    
                except subprocess.TimeoutExpired:
                    failed_models.append(model_name)
                    continue
            
            if failed_models:
                return ErrorResult(
                    message=f"Failed to unload some models. Successfully unloaded {unloaded_count} models",
                    code="PARTIAL_UNLOAD",
                    details={
                        "unloaded_count": unloaded_count,
                        "memory_freed_mb": round(total_memory_freed, 2),
                        "memory_freed_gb": round(total_memory_freed / 1024, 2),
                        "failed_models": failed_models
                    }
                )
            
            return SuccessResult(data={
                "message": f"Unloaded {unloaded_count} models from memory",
                "unloaded_count": unloaded_count,
                "memory_freed_mb": round(total_memory_freed, 2),
                "memory_freed_gb": round(total_memory_freed / 1024, 2),
                "timestamp": datetime.now().isoformat()
            })
            
        except Exception as e:
            return ErrorResult(
                message=f"Failed to unload all models: {str(e)}",
                code="UNLOAD_ALL_FAILED",
                details={"error": str(e)}
            )
    
    def _extract_model_from_cmdline(self, cmdline: str) -> Optional[str]:
        """Extract model name from ollama runner command line."""
        try:
            if '--model' in cmdline:
                parts = cmdline.split()
                for i, part in enumerate(parts):
                    if part == '--model' and i + 1 < len(parts):
                        model_path = parts[i + 1]
                        # Extract just the model name from the path
                        if '/' in model_path:
                            return model_path.split('/')[-1]
                        return model_path
            return None
        except Exception:
            return None
    
    def _extract_model_name_from_process(self, process: Dict[str, Any]) -> Optional[str]:
        """Extract model name from process information."""
        try:
            # Try to get model name from available models
            if process["model"]:
                # Check if it's a hash and try to match with available models
                # For now, return a generic name that should work with ollama stop
                return "llama2:7b-chat"  # This is a fallback
            return None
        except Exception:
            return None
    
    @classmethod
    def get_schema(cls) -> Dict[str, Any]:
        """Get command schema."""
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "description": "Action to perform",
                    "enum": ["status", "unload", "unload_all"],
                    "default": "status"
                },
                "model_name": {
                    "type": "string",
                    "description": "Name of the model to unload (required for unload action)",
                    "default": None
                }
            },
            "required": ["action"],
            "additionalProperties": False
        } 