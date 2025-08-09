"""Vast.ai instances command for listing active GPU instances."""

import asyncio
import json
from typing import Dict, Any, Optional
from mcp_proxy_adapter.commands.base import Command
from mcp_proxy_adapter.commands.result import SuccessResult, ErrorResult
from mcp_proxy_adapter.config import config


class VastInstancesCommand(Command):
    """List active GPU instances on Vast.ai."""
    
    name = "vast_instances"
    
    async def execute(
        self,
        show_all: bool = False,
        **kwargs
    ) -> SuccessResult:
        """List active GPU instances.
        
        Args:
            show_all: Show all instances including terminated ones
            
        Returns:
            SuccessResult with instances list
        """
        try:
            # Get Vast API configuration
            api_key = config.get("vast.api_key")
            api_url = config.get("vast.api_url", "https://console.vast.ai/api/v0")
            
            if not api_key or api_key == "your-vast-api-key-here":
                return ErrorResult(
                    message="Vast API key not configured",
                    code="MISSING_API_KEY",
                    details={"config_path": "vast.api_key"}
                )
            
            # Build API URL
            instances_url = f"{api_url}/instances/"
            if not show_all:
                instances_url += "?owner=me"
            
            # Execute curl request
            curl_cmd = [
                "curl", "-s",
                "-H", f"Authorization: Bearer {api_key}",
                instances_url
            ]
            
            process = await asyncio.create_subprocess_exec(
                *curl_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                error_msg = stderr.decode('utf-8').strip()
                return ErrorResult(
                    message=f"Failed to get Vast instances: {error_msg}",
                    code="API_REQUEST_FAILED",
                    details={
                        "stderr": error_msg,
                        "exit_code": process.returncode,
                        "url": instances_url
                    }
                )
            
            # Parse response
            try:
                response_data = json.loads(stdout.decode('utf-8'))
            except json.JSONDecodeError as e:
                return ErrorResult(
                    message=f"Failed to parse API response: {str(e)}",
                    code="INVALID_JSON_RESPONSE",
                    details={"raw_response": stdout.decode('utf-8')[:500]}
                )
            
            # Process instances
            if not isinstance(response_data, dict) or "instances" not in response_data:
                return ErrorResult(
                    message="Unexpected API response format",
                    code="UNEXPECTED_RESPONSE",
                    details={"response": response_data}
                )
            
            instances = response_data.get("instances", [])
            
            # Format instances for better readability
            formatted_instances = []
            for instance in instances:
                formatted_instance = {
                    "id": instance.get("id"),
                    "label": instance.get("label"),
                    "machine_id": instance.get("machine_id"),
                    "status": instance.get("actual_status"),
                    "intended_status": instance.get("intended_status"),
                    "image": instance.get("image"),
                    "gpu_name": instance.get("gpu_name"),
                    "gpu_count": instance.get("num_gpus", 0),
                    "cpu_cores": instance.get("cpu_cores", 0),
                    "cpu_ram": instance.get("cpu_ram", 0),
                    "disk_space": instance.get("disk_space", 0),
                    "price_per_hour": instance.get("dph_total", 0),
                    "location": instance.get("geolocation"),
                    "ssh_host": instance.get("ssh_host"),
                    "ssh_port": instance.get("ssh_port"),
                    "jupyter_token": instance.get("jupyter_token"),
                    "direct_port_start": instance.get("direct_port_start"),
                    "direct_port_end": instance.get("direct_port_end"),
                    "start_date": instance.get("start_date"),
                    "end_date": instance.get("end_date"),
                    "duration": instance.get("duration"),
                    "cur_state": instance.get("cur_state"),
                    "next_state": instance.get("next_state"),
                    "reliability": instance.get("reliability2", 0),
                    "score": instance.get("score", 0)
                }
                
                # Add connection info if available
                if formatted_instance["ssh_host"] and formatted_instance["ssh_port"]:
                    formatted_instance["ssh_command"] = f"ssh -p {formatted_instance['ssh_port']} root@{formatted_instance['ssh_host']}"
                
                if formatted_instance["jupyter_token"]:
                    formatted_instance["jupyter_url"] = f"http://{formatted_instance['ssh_host']}:8080/?token={formatted_instance['jupyter_token']}"
                
                formatted_instances.append(formatted_instance)
            
            # Calculate statistics
            stats = {
                "total_instances": len(formatted_instances),
                "running_instances": len([i for i in formatted_instances if i["status"] == "running"]),
                "loading_instances": len([i for i in formatted_instances if i["status"] == "loading"]),
                "stopped_instances": len([i for i in formatted_instances if i["status"] in ["stopped", "exited"]]),
                "total_cost_per_hour": sum(i["price_per_hour"] for i in formatted_instances if i["price_per_hour"]),
                "gpu_types": {},
                "statuses": {}
            }
            
            # Count GPU types and statuses
            for instance in formatted_instances:
                gpu = instance["gpu_name"]
                if gpu:
                    stats["gpu_types"][gpu] = stats["gpu_types"].get(gpu, 0) + 1
                
                status = instance["status"]
                if status:
                    stats["statuses"][status] = stats["statuses"].get(status, 0) + 1
            
            return SuccessResult(data={
                "status": "success",
                "message": f"Found {len(formatted_instances)} instances",
                "instances": formatted_instances,
                "statistics": stats,
                "show_all": show_all,
                "connection_help": {
                    "ssh": "Use 'ssh_command' field for direct SSH access",
                    "jupyter": "Use 'jupyter_url' field for Jupyter access (if available)",
                    "ports": "Direct ports range from 'direct_port_start' to 'direct_port_end'"
                }
            })
            
        except Exception as e:
            return ErrorResult(
                message=f"Unexpected error getting Vast instances: {str(e)}",
                code="UNEXPECTED_ERROR",
                details={"error_type": type(e).__name__}
            )
    
    @classmethod
    def get_schema(cls) -> Dict[str, Any]:
        """Get the JSON schema for this command."""
        return {
            "type": "object",
            "properties": {
                "show_all": {
                    "type": "boolean",
                    "description": "Show all instances including terminated ones",
                    "default": False
                }
            },
            "required": [],
            "additionalProperties": False
        } 