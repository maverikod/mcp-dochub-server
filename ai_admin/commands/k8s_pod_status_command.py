"""Kubernetes pod status command for MCP server."""

import re
import subprocess
import json
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime

from mcp_proxy_adapter.commands.base import Command
from mcp_proxy_adapter.commands.result import SuccessResult, ErrorResult


class K8sPodStatusCommand(Command):
    """Command to get status of Kubernetes pods."""
    
    name = "k8s_pod_status"
    
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
                     all_ai_admin: bool = False,
                     **kwargs):
        """
        Get status of Kubernetes pods.
        
        Args:
            pod_name: Name of specific pod to check (if not provided, derived from project_path)
            project_path: Path to project directory (used to derive pod name)
            namespace: Kubernetes namespace
            all_ai_admin: Get status of all ai-admin pods
        """
        try:
            if all_ai_admin:
                # Get all ai-admin pods
                cmd = [
                    "kubectl", "get", "pods", "-n", namespace,
                    "-l", "app=ai-admin",
                    "-o", "json"
                ]
                result = subprocess.run(cmd, capture_output=True, text=True)
                
                if result.returncode != 0:
                    return ErrorResult(
                        message=f"Failed to get pods: {result.stderr}",
                        code="KUBECTL_FAILED",
                        details={}
                    )
                
                pods_data = json.loads(result.stdout)
                pods_info = []
                
                for pod in pods_data.get("items", []):
                    pod_info = self._extract_pod_info(pod)
                    pods_info.append(pod_info)
                
                return SuccessResult(data={
                    "message": f"Found {len(pods_info)} ai-admin pods",
                    "namespace": namespace,
                    "pods": pods_info,
                    "timestamp": datetime.now().isoformat()
                })
            
            else:
                # Get specific pod
                if not pod_name:
                    if not project_path:
                        import os
                        project_path = os.getcwd()
                    
                    project_name = self.get_project_name(project_path)
                    pod_name = f"ai-admin-{project_name}"
                
                cmd = ["kubectl", "get", "pod", pod_name, "-n", namespace, "-o", "json"]
                result = subprocess.run(cmd, capture_output=True, text=True)
                
                if result.returncode != 0:
                    return ErrorResult(
                        message=f"Pod {pod_name} not found in namespace {namespace}",
                        code="POD_NOT_FOUND",
                        details={}
                    )
                
                pod_data = json.loads(result.stdout)
                pod_info = self._extract_pod_info(pod_data)
                
                return SuccessResult(data={
                    "message": f"Pod {pod_name} status retrieved",
                    "namespace": namespace,
                    "pod": pod_info,
                    "timestamp": datetime.now().isoformat()
                })
            
        except Exception as e:
            return ErrorResult(
                message=f"Unexpected error getting pod status: {str(e)}",
                code="UNEXPECTED_ERROR",
                details={}
            )
    
    def _extract_pod_info(self, pod_data: Dict) -> Dict:
        """Extract useful information from pod JSON data."""
        metadata = pod_data.get("metadata", {})
        status = pod_data.get("status", {})
        spec = pod_data.get("spec", {})
        
        # Get container statuses
        container_statuses = []
        for container_status in status.get("containerStatuses", []):
            container_info = {
                "name": container_status.get("name"),
                "ready": container_status.get("ready", False),
                "restart_count": container_status.get("restartCount", 0),
                "image": container_status.get("image"),
                "state": container_status.get("state", {})
            }
            container_statuses.append(container_info)
        
        # Get mounted volumes info
        volumes = []
        for volume in spec.get("volumes", []):
            if "hostPath" in volume:
                volumes.append({
                    "name": volume.get("name"),
                    "type": "hostPath",
                    "path": volume.get("hostPath", {}).get("path")
                })
        
        return {
            "name": metadata.get("name"),
            "namespace": metadata.get("namespace"),
            "labels": metadata.get("labels", {}),
            "creation_timestamp": metadata.get("creationTimestamp"),
            "phase": status.get("phase"),
            "pod_ip": status.get("podIP"),
            "host_ip": status.get("hostIP"),
            "node_name": spec.get("nodeName"),
            "containers": container_statuses,
            "volumes": volumes,
            "restart_policy": spec.get("restartPolicy")
        }
    
    @classmethod
    def get_schema(cls) -> Dict[str, Any]:
        """Get JSON schema for k8s pod status command parameters."""
        return {
            "type": "object",
            "properties": {
                "pod_name": {
                    "type": "string",
                    "description": "Name of specific pod to check (if not provided, derived from project_path)"
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
                            "all_ai_admin": {
                "type": "boolean",
                "description": "Get status of all ai-admin pods",
                    "default": False
                }
            }
        } 