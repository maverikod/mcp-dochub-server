import subprocess
import json
import psutil
import os
from typing import Dict, Any, List
from datetime import datetime
from mcp_proxy_adapter.commands.base import Command
from mcp_proxy_adapter.commands.result import SuccessResult, ErrorResult
from ai_admin.commands.ollama_base import ollama_config

class OllamaStatusCommand(Command):
    """Check Ollama status and models in memory."""
    
    name = "ollama_status"
    
    async def execute(self, **kwargs):
        """Execute Ollama status check.
        
        Returns:
            Success or error result with status information
        """
        try:
            return await self._get_status()
        except Exception as e:
            return ErrorResult(
                message=f"Ollama status check failed: {str(e)}",
                code="OLLAMA_STATUS_ERROR",
                details={"error": str(e)}
            )
    
    async def _get_status(self) -> SuccessResult:
        """Get comprehensive Ollama status."""
        try:
            # Check if Ollama service is running
            service_status = await self._check_service_status()
            
            # Get models list
            models_status = await self._get_models_status()
            
            # Get memory usage
            memory_status = await self._get_memory_status()
            
            # Get running processes
            processes_status = await self._get_processes_status()
            
            return SuccessResult(data={
                "message": "Ollama status retrieved successfully",
                "service": service_status,
                "models": models_status,
                "memory": memory_status,
                "processes": processes_status,
                "config": {
                    "models_cache_path": ollama_config.get_models_cache_path(),
                    "host": ollama_config.get_ollama_host(),
                    "port": ollama_config.get_ollama_port(),
                    "timeout": ollama_config.get_ollama_timeout()
                },
                "timestamp": datetime.now().isoformat()
            })
            
        except Exception as e:
            return ErrorResult(
                message=f"Failed to get Ollama status: {str(e)}",
                code="STATUS_CHECK_FAILED",
                details={"error": str(e)}
            )
    
    async def _check_service_status(self) -> Dict[str, Any]:
        """Check if Ollama service is running."""
        try:
            # Check if ollama serve process is running
            result = subprocess.run(
                ["pgrep", "-f", "ollama serve"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            is_running = result.returncode == 0
            pid = result.stdout.strip() if is_running else None
            
            return {
                "running": is_running,
                "pid": pid,
                "status": "active" if is_running else "stopped"
            }
            
        except subprocess.TimeoutExpired:
            return {
                "running": False,
                "pid": None,
                "status": "timeout"
            }
    
    async def _get_models_status(self) -> Dict[str, Any]:
        """Get models list and status."""
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
                return {
                    "available": [],
                    "count": 0,
                    "error": result.stderr
                }
            
            # Parse output
            output_lines = result.stdout.strip().split('\n')
            models = []
            
            # Skip header line and parse each model line
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
                        models.append(model_info)
            
            return {
                "available": models,
                "count": len(models),
                "raw_output": result.stdout
            }
            
        except subprocess.TimeoutExpired:
            return {
                "available": [],
                "count": 0,
                "error": "timeout"
            }
    
    async def _get_memory_status(self) -> Dict[str, Any]:
        """Get memory usage information."""
        try:
            # Get system memory info
            memory = psutil.virtual_memory()
            
            # Get Ollama processes memory usage
            ollama_memory = 0
            ollama_processes = []
            
            for proc in psutil.process_iter(['pid', 'name', 'memory_info']):
                try:
                    if 'ollama' in proc.info['name'].lower():
                        memory_info = proc.memory_info()
                        ollama_memory += memory_info.rss
                        ollama_processes.append({
                            "pid": proc.info['pid'],
                            "name": proc.info['name'],
                            "memory_mb": round(memory_info.rss / 1024 / 1024, 2)
                        })
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            return {
                "system_total_gb": round(memory.total / 1024 / 1024 / 1024, 2),
                "system_used_gb": round(memory.used / 1024 / 1024 / 1024, 2),
                "system_available_gb": round(memory.available / 1024 / 1024 / 1024, 2),
                "system_percent": memory.percent,
                "ollama_total_mb": round(ollama_memory / 1024 / 1024, 2),
                "ollama_processes": ollama_processes,
                "ollama_process_count": len(ollama_processes)
            }
            
        except Exception as e:
            return {
                "error": str(e),
                "ollama_processes": [],
                "ollama_process_count": 0
            }
    
    async def _get_processes_status(self) -> Dict[str, Any]:
        """Get detailed Ollama processes information."""
        try:
            processes = []
            
            for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'memory_info', 'cpu_percent']):
                try:
                    if 'ollama' in proc.info['name'].lower():
                        cmdline = ' '.join(proc.info['cmdline']) if proc.info['cmdline'] else ''
                        memory_mb = round(proc.info['memory_info'].rss / 1024 / 1024, 2)
                        
                        process_info = {
                            "pid": proc.info['pid'],
                            "name": proc.info['name'],
                            "cmdline": cmdline,
                            "memory_mb": memory_mb,
                            "cpu_percent": round(proc.info['cpu_percent'], 2) if proc.info['cpu_percent'] else 0
                        }
                        
                        # Determine process type
                        if 'serve' in cmdline:
                            process_info["type"] = "server"
                        elif 'runner' in cmdline:
                            process_info["type"] = "model_runner"
                        else:
                            process_info["type"] = "other"
                        
                        processes.append(process_info)
                        
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            return {
                "processes": processes,
                "count": len(processes),
                "server_processes": len([p for p in processes if p["type"] == "server"]),
                "runner_processes": len([p for p in processes if p["type"] == "model_runner"])
            }
            
        except Exception as e:
            return {
                "error": str(e),
                "processes": [],
                "count": 0
            }
    
    @classmethod
    def get_schema(cls) -> Dict[str, Any]:
        """Get command schema."""
        return {
            "type": "object",
            "properties": {},
            "additionalProperties": False
        } 