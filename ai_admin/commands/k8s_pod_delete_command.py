"""Kubernetes pod deletion command for MCP server."""

import re
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime

from mcp_proxy_adapter.commands.base import Command
from mcp_proxy_adapter.commands.result import SuccessResult, ErrorResult


class K8sPodDeleteCommand(Command):
    """Command to delete Kubernetes pods."""
    
    name = "k8s_pod_delete"
    
    def get_project_name(self, project_path: str) -> str:
        """Extract and sanitize project name from path."""
        project_name = Path(project_path).name
        # Convert to kubernetes-compatible name (lowercase, no special chars)
        sanitized = re.sub(r'[^a-z0-9]', '-', project_name.lower())
        return sanitized.strip('-')
    
    async def execute(self, 
                     pod_name: Optional[str] = None,
                     project_path: Optional[str] = None,
                     namespace: str = "default",
                     force: bool = False,
                     **kwargs):
        """
        Delete Kubernetes pod.
        
        Args:
            pod_name: Name of pod to delete (if not provided, derived from project_path)
            project_path: Path to project directory (used to derive pod name)
            namespace: Kubernetes namespace
            force: Force delete pod immediately
        """
        try:
            # Determine pod name
            if not pod_name:
                if not project_path:
                    import os
                    project_path = os.getcwd()
                
                project_name = self.get_project_name(project_path)
                pod_name = f"ai-admin-{project_name}"
            
            # Check if pod exists
            check_cmd = ["kubectl", "get", "pod", pod_name, "-n", namespace]
            check_result = subprocess.run(check_cmd, capture_output=True, text=True)
            
            if check_result.returncode != 0:
                return ErrorResult(
                    message=f"Pod {pod_name} not found in namespace {namespace}",
                    code="POD_NOT_FOUND",
                    details={}
                )
            
            # Delete the pod
            delete_cmd = ["kubectl", "delete", "pod", pod_name, "-n", namespace]
            if force:
                delete_cmd.extend(["--force", "--grace-period=0"])
            
            delete_result = subprocess.run(delete_cmd, capture_output=True, text=True)
            
            if delete_result.returncode != 0:
                return ErrorResult(
                    message=f"Failed to delete pod: {delete_result.stderr}",
                    code="POD_DELETE_FAILED",
                    details={}
                )
            
            return SuccessResult(data={
                "message": f"Successfully deleted pod {pod_name}",
                "pod_name": pod_name,
                "namespace": namespace,
                "force": force,
                "timestamp": datetime.now().isoformat()
            })
            
        except Exception as e:
            return ErrorResult(
                message=f"Unexpected error deleting pod: {str(e)}",
                code="UNEXPECTED_ERROR",
                details={}
            )
    
    @classmethod
    def get_schema(cls) -> Dict[str, Any]:
        """Get JSON schema for k8s pod delete command parameters."""
        return {
            "type": "object",
            "properties": {
                "pod_name": {
                    "type": "string",
                    "description": "Name of pod to delete (if not provided, derived from project_path)"
                },
                "project_path": {
                    "type": "string",
                    "description": "Path to project directory (used to derive pod name)"
                },
                "namespace": {
                    "type": "string",
                    "description": "Kubernetes namespace",
                    "default": "default"
                },
                "force": {
                    "type": "boolean",
                    "description": "Force delete pod immediately",
                    "default": False
                }
            }
        } 