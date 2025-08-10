import subprocess
import json
import psutil
import os
from typing import Dict, Any, List, Optional
from datetime import datetime
from mcp_proxy_adapter.commands.base import Command
from mcp_proxy_adapter.commands.result import SuccessResult, ErrorResult

class SystemMonitorCommand(Command):
    """Monitor system resources: memory, temperature, GPU metrics."""
    
    name = "system_monitor"
    
    async def execute(self, 
                     include_gpu: bool = True,
                     include_temperature: bool = True,
                     include_processes: bool = False,
                     **kwargs):
        """Execute system monitoring.
        
        Args:
            include_gpu: Include GPU metrics if available
            include_temperature: Include temperature sensors
            include_processes: Include top processes by memory/CPU
            
        Returns:
            Success or error result with system metrics
        """
        try:
            return await self._get_system_metrics(
                include_gpu=include_gpu,
                include_temperature=include_temperature,
                include_processes=include_processes
            )
        except Exception as e:
            return ErrorResult(
                message=f"System monitoring failed: {str(e)}",
                code="SYSTEM_MONITOR_ERROR",
                details={"error": str(e)}
            )
    
    async def _get_system_metrics(self, 
                                 include_gpu: bool = True,
                                 include_temperature: bool = True,
                                 include_processes: bool = False) -> SuccessResult:
        """Get comprehensive system metrics."""
        try:
            metrics = {
                "timestamp": datetime.now().isoformat(),
                "system": await self._get_system_info(),
                "memory": await self._get_memory_info(),
                "cpu": await self._get_cpu_info(),
                "disk": await self._get_disk_info(),
                "network": await self._get_network_info()
            }
            
            if include_temperature:
                metrics["temperature"] = await self._get_temperature_info()
            
            if include_gpu:
                metrics["gpu"] = await self._get_gpu_info()
            
            if include_processes:
                metrics["processes"] = await self._get_top_processes()
            
            return SuccessResult(data={
                "message": "System metrics retrieved successfully",
                "metrics": metrics
            })
            
        except Exception as e:
            return ErrorResult(
                message=f"Failed to get system metrics: {str(e)}",
                code="METRICS_FAILED",
                details={"error": str(e)}
            )
    
    async def _get_system_info(self) -> Dict[str, Any]:
        """Get basic system information."""
        try:
            uname = os.uname()
            boot_time = datetime.fromtimestamp(psutil.boot_time())
            uptime = datetime.now() - boot_time
            
            return {
                "hostname": uname.nodename,
                "os": uname.sysname,
                "release": uname.release,
                "version": uname.version,
                "architecture": uname.machine,
                "boot_time": boot_time.isoformat(),
                "uptime_seconds": int(uptime.total_seconds()),
                "uptime_formatted": str(uptime).split('.')[0]  # Remove microseconds
            }
        except Exception as e:
            return {"error": str(e)}
    
    async def _get_memory_info(self) -> Dict[str, Any]:
        """Get detailed memory information."""
        try:
            memory = psutil.virtual_memory()
            swap = psutil.swap_memory()
            
            return {
                "ram": {
                    "total_gb": round(memory.total / 1024 / 1024 / 1024, 2),
                    "used_gb": round(memory.used / 1024 / 1024 / 1024, 2),
                    "available_gb": round(memory.available / 1024 / 1024 / 1024, 2),
                    "free_gb": round(memory.free / 1024 / 1024 / 1024, 2),
                    "percent_used": memory.percent,
                    "percent_available": round((memory.available / memory.total) * 100, 2)
                },
                "swap": {
                    "total_gb": round(swap.total / 1024 / 1024 / 1024, 2),
                    "used_gb": round(swap.used / 1024 / 1024 / 1024, 2),
                    "free_gb": round(swap.free / 1024 / 1024 / 1024, 2),
                    "percent_used": swap.percent
                }
            }
        except Exception as e:
            return {"error": str(e)}
    
    async def _get_cpu_info(self) -> Dict[str, Any]:
        """Get CPU information and usage."""
        try:
            cpu_count = psutil.cpu_count()
            cpu_freq = psutil.cpu_freq()
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_percent_per_core = psutil.cpu_percent(interval=1, percpu=True)
            
            # Get CPU load average
            load_avg = os.getloadavg()
            
            return {
                "cores": {
                    "physical": psutil.cpu_count(logical=False),
                    "logical": cpu_count,
                    "usage_percent": cpu_percent,
                    "usage_per_core": cpu_percent_per_core
                },
                "frequency": {
                    "current_mhz": round(cpu_freq.current, 2) if cpu_freq else None,
                    "min_mhz": round(cpu_freq.min, 2) if cpu_freq else None,
                    "max_mhz": round(cpu_freq.max, 2) if cpu_freq else None
                },
                "load_average": {
                    "1min": round(load_avg[0], 2),
                    "5min": round(load_avg[1], 2),
                    "15min": round(load_avg[2], 2)
                }
            }
        except Exception as e:
            return {"error": str(e)}
    
    async def _get_disk_info(self) -> Dict[str, Any]:
        """Get disk usage information."""
        try:
            disk_usage = psutil.disk_usage('/')
            disk_io = psutil.disk_io_counters()
            
            return {
                "root": {
                    "total_gb": round(disk_usage.total / 1024 / 1024 / 1024, 2),
                    "used_gb": round(disk_usage.used / 1024 / 1024 / 1024, 2),
                    "free_gb": round(disk_usage.free / 1024 / 1024 / 1024, 2),
                    "percent_used": disk_usage.percent
                },
                "io": {
                    "read_count": disk_io.read_count if disk_io else 0,
                    "write_count": disk_io.write_count if disk_io else 0,
                    "read_bytes_gb": round(disk_io.read_bytes / 1024 / 1024 / 1024, 2) if disk_io else 0,
                    "write_bytes_gb": round(disk_io.write_bytes / 1024 / 1024 / 1024, 2) if disk_io else 0
                }
            }
        except Exception as e:
            return {"error": str(e)}
    
    async def _get_network_info(self) -> Dict[str, Any]:
        """Get network information."""
        try:
            net_io = psutil.net_io_counters()
            net_if_addrs = psutil.net_if_addrs()
            
            return {
                "bytes": {
                    "bytes_sent_gb": round(net_io.bytes_sent / 1024 / 1024 / 1024, 2),
                    "bytes_recv_gb": round(net_io.bytes_recv / 1024 / 1024 / 1024, 2)
                },
                "packets": {
                    "packets_sent": net_io.packets_sent,
                    "packets_recv": net_io.packets_recv
                },
                "interfaces": len(net_if_addrs)
            }
        except Exception as e:
            return {"error": str(e)}
    
    async def _get_temperature_info(self) -> Dict[str, Any]:
        """Get temperature sensor information."""
        try:
            temperatures = {}
            
            # Try to get CPU temperature
            try:
                # Common paths for CPU temperature
                temp_paths = [
                    "/sys/class/thermal/thermal_zone0/temp",
                    "/sys/class/hwmon/hwmon0/temp1_input",
                    "/sys/class/hwmon/hwmon1/temp1_input"
                ]
                
                for path in temp_paths:
                    if os.path.exists(path):
                        with open(path, 'r') as f:
                            temp_raw = int(f.read().strip())
                            temp_celsius = temp_raw / 1000.0 if temp_raw > 1000 else temp_raw
                            temperatures["cpu"] = {
                                "celsius": round(temp_celsius, 1),
                                "fahrenheit": round(temp_celsius * 9/5 + 32, 1),
                                "source": path
                            }
                            break
            except Exception:
                pass
            
            # Try to get GPU temperature using nvidia-smi
            try:
                result = subprocess.run(
                    ["nvidia-smi", "--query-gpu=temperature.gpu", "--format=csv,noheader,nounits"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
                if result.returncode == 0:
                    gpu_temp = int(result.stdout.strip())
                    temperatures["gpu"] = {
                        "celsius": gpu_temp,
                        "fahrenheit": round(gpu_temp * 9/5 + 32, 1),
                        "source": "nvidia-smi"
                    }
            except Exception:
                pass
            
            return temperatures if temperatures else {"error": "No temperature sensors found"}
            
        except Exception as e:
            return {"error": str(e)}
    
    async def _get_gpu_info(self) -> Dict[str, Any]:
        """Get GPU information and metrics."""
        try:
            gpu_info = {}
            
            # Try NVIDIA GPU
            try:
                result = subprocess.run(
                    ["nvidia-smi", "--query-gpu=name,memory.total,memory.used,memory.free,utilization.gpu,temperature.gpu,power.draw", "--format=csv,noheader,nounits"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
                if result.returncode == 0:
                    lines = result.stdout.strip().split('\n')
                    gpus = []
                    
                    for line in lines:
                        if line.strip():
                            parts = line.split(', ')
                            if len(parts) >= 7:
                                gpu_data = {
                                    "name": parts[0],
                                    "memory_total_mb": int(parts[1]),
                                    "memory_used_mb": int(parts[2]),
                                    "memory_free_mb": int(parts[3]),
                                    "utilization_percent": int(parts[4]),
                                    "temperature_celsius": int(parts[5]),
                                    "power_draw_w": float(parts[6]) if parts[6] != "N/A" else None
                                }
                                gpu_data["memory_used_percent"] = round((gpu_data["memory_used_mb"] / gpu_data["memory_total_mb"]) * 100, 1)
                                gpus.append(gpu_data)
                    
                    gpu_info["nvidia"] = {
                        "gpus": gpus,
                        "count": len(gpus)
                    }
            except Exception:
                pass
            
            # Try AMD GPU (rocm-smi)
            try:
                result = subprocess.run(
                    ["rocm-smi", "--showproductname", "--showmeminfo", "vram", "--showtemp", "--showpower"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
                if result.returncode == 0:
                    gpu_info["amd"] = {
                        "available": True,
                        "raw_output": result.stdout
                    }
            except Exception:
                pass
            
            return gpu_info if gpu_info else {"error": "No GPU information available"}
            
        except Exception as e:
            return {"error": str(e)}
    
    async def _get_top_processes(self) -> Dict[str, Any]:
        """Get top processes by memory and CPU usage."""
        try:
            processes = []
            
            for proc in psutil.process_iter(['pid', 'name', 'memory_info', 'cpu_percent']):
                try:
                    memory_info = proc.memory_info()
                    cpu_percent = proc.cpu_percent()
                    
                    if memory_info.rss > 0:  # Only include processes using memory
                        process_info = {
                            "pid": proc.info['pid'],
                            "name": proc.info['name'],
                            "memory_mb": round(memory_info.rss / 1024 / 1024, 2),
                            "cpu_percent": round(cpu_percent, 2)
                        }
                        processes.append(process_info)
                        
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            # Sort by memory usage and get top 10
            processes.sort(key=lambda x: x['memory_mb'], reverse=True)
            top_memory = processes[:10]
            
            # Sort by CPU usage and get top 10
            processes.sort(key=lambda x: x['cpu_percent'], reverse=True)
            top_cpu = processes[:10]
            
            return {
                "top_memory": top_memory,
                "top_cpu": top_cpu
            }
            
        except Exception as e:
            return {"error": str(e)}
    
    @classmethod
    def get_schema(cls) -> Dict[str, Any]:
        """Get command schema."""
        return {
            "type": "object",
            "properties": {
                "include_gpu": {
                    "type": "boolean",
                    "description": "Include GPU metrics if available",
                    "default": True
                },
                "include_temperature": {
                    "type": "boolean", 
                    "description": "Include temperature sensors",
                    "default": True
                },
                "include_processes": {
                    "type": "boolean",
                    "description": "Include top processes by memory/CPU",
                    "default": False
                }
            },
            "additionalProperties": False
        } 