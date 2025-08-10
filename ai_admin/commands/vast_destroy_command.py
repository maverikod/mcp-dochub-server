"""Vast.ai destroy instance command for stopping/deleting GPU instances."""

import asyncio
import json
from typing import Dict, Any
from mcp_proxy_adapter.commands.base import Command
from mcp_proxy_adapter.commands.result import SuccessResult, ErrorResult
from mcp_proxy_adapter.config import config


class VastDestroyCommand(Command):
    """Destroy (stop/delete) a GPU instance on Vast.ai."""
    
    name = "vast_destroy"
    
    async def execute(
        self,
        instance_id: int,
        **kwargs
    ) -> SuccessResult:
        """Destroy a GPU instance.
        
        Args:
            instance_id: ID of the instance to destroy
            
        Returns:
            SuccessResult with destruction details
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
            
            # Execute curl request to destroy instance
            curl_cmd = [
                "curl", "-s", "-X", "DELETE",
                "-H", f"Authorization: Bearer {api_key}",
                f"{api_url}/instances/{instance_id}/"
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
                    message=f"Failed to destroy Vast instance: {error_msg}",
                    code="API_REQUEST_FAILED",
                    details={
                        "stderr": error_msg,
                        "exit_code": process.returncode,
                        "instance_id": instance_id
                    }
                )
            
            # Parse response
            response_text = stdout.decode('utf-8').strip()
            
            # Try to parse as JSON, but handle simple text responses too
            try:
                response_data = json.loads(response_text) if response_text else {}
            except json.JSONDecodeError:
                # Sometimes API returns simple text responses
                response_data = {"message": response_text}
            
            # Check for API errors
            if "error" in response_data:
                return ErrorResult(
                    message=f"Vast API error: {response_data['error']}",
                    code="API_ERROR",
                    details={"api_response": response_data}
                )
            
            # Successful destruction
            return SuccessResult(data={
                "status": "success",
                "message": f"Successfully destroyed instance {instance_id}",
                "instance_id": instance_id,
                "api_response": response_data,
                "info": [
                    "Instance has been marked for destruction",
                    "It may take a few moments to fully terminate",
                    "Billing for this instance will stop shortly",
                    "Use 'vast_instances' to verify termination status"
                ]
            })
            
        except Exception as e:
            return ErrorResult(
                message=f"Unexpected error destroying Vast instance: {str(e)}",
                code="UNEXPECTED_ERROR",
                details={"error_type": type(e).__name__}
            )
    
    @classmethod
    def get_schema(cls) -> Dict[str, Any]:
        """Get the JSON schema for this command."""
        return {
            "type": "object",
            "properties": {
                "instance_id": {
                    "type": "integer",
                    "description": "ID of the instance to destroy (get from vast_instances command)"
                }
            },
            "required": ["instance_id"],
            "additionalProperties": False
        } 