"""Kubernetes pod creation command for MCP server."""

import os
import re
import subprocess
import yaml
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime

from mcp_proxy_adapter.commands.base import Command
from mcp_proxy_adapter.commands.result import SuccessResult, ErrorResult


class K8sPodCreateCommand(Command):
    """Command to create Kubernetes pods for projects."""
    
    name = "k8s_pod_create"
    
    def get_project_name(self, project_path: str) -> str:
        """Extract and sanitize project name from path."""
        project_name = Path(project_path).name
        # Convert to kubernetes-compatible name (lowercase, no special chars)
        sanitized = re.sub(r'[^a-z0-9]', '-', project_name.lower())
        return sanitized.strip('-')
    
    async def execute(self, 
                     project_path: Optional[str] = None,
                     image: str = "ai-admin-server:latest",
                     port: int = 8060,
                     namespace: str = "default",
                     cpu_limit: str = "500m",
                     memory_limit: str = "512Mi",
                     **kwargs):
        """
        Create Kubernetes pod for project with mounted directory.
        
        Args:
            project_path: Path to project directory (defaults to current working directory)
            image: Docker image to use
            port: Port to expose
            namespace: Kubernetes namespace
            cpu_limit: CPU limit for pod
            memory_limit: Memory limit for pod
        """
        try:
            # Get current working directory if path not provided
            if not project_path:
                project_path = os.getcwd()
            
            # Ensure path exists
            if not os.path.exists(project_path):
                return ErrorResult(
                    message=f"Project path does not exist: {project_path}",
                    code="PATH_NOT_FOUND",
                    details={}
                )
            
            project_name = self.get_project_name(project_path)
            pod_name = f"ai-admin-{project_name}"
            
            # Create pod YAML configuration
            pod_config = {
                "apiVersion": "v1",
                "kind": "Pod",
                "metadata": {
                    "name": pod_name,
                    "namespace": namespace,
                    "labels": {
                        "app": "ai-admin",
                        "project": project_name
                    }
                },
                "spec": {
                    "containers": [{
                        "name": "mcp-server",
                        "image": image,
                        "ports": [{
                            "containerPort": port,
                            "name": "http"
                        }],
                        "volumeMounts": [{
                            "name": "project-volume",
                            "mountPath": "/app"
                        }],
                        "resources": {
                            "limits": {
                                "cpu": cpu_limit,
                                "memory": memory_limit
                            },
                            "requests": {
                                "cpu": "100m",
                                "memory": "128Mi"
                            }
                        },
                        "env": [{
                            "name": "PROJECT_PATH",
                            "value": "/app"
                        }]
                    }],
                    "volumes": [{
                        "name": "project-volume",
                        "hostPath": {
                            "path": project_path,
                            "type": "Directory"
                        }
                    }],
                    "restartPolicy": "Always"
                }
            }
            
            # Convert to YAML
            yaml_content = yaml.dump(pod_config, default_flow_style=False)
            
            # Save YAML to temporary file
            yaml_file = f"/tmp/{pod_name}.yaml"
            with open(yaml_file, 'w') as f:
                f.write(yaml_content)
            
            # Check if pod already exists
            check_cmd = ["kubectl", "get", "pod", pod_name, "-n", namespace]
            check_result = subprocess.run(check_cmd, capture_output=True, text=True)
            
            if check_result.returncode == 0:
                return SuccessResult(data={
                    "message": f"Pod {pod_name} already exists in namespace {namespace}",
                    "pod_name": pod_name,
                    "namespace": namespace,
                    "project_path": project_path,
                    "project_name": project_name,
                    "status": "already_exists",
                    "yaml_file": yaml_file
                })
            
            # Create the pod
            create_cmd = ["kubectl", "apply", "-f", yaml_file]
            create_result = subprocess.run(create_cmd, capture_output=True, text=True)
            
            if create_result.returncode != 0:
                return ErrorResult(
                    message=f"Failed to create pod: {create_result.stderr}",
                    code="POD_CREATE_FAILED",
                    details={"yaml_content": yaml_content}
                )
            
            # Wait a bit and get pod status
            import time
            time.sleep(2)
            
            status_cmd = ["kubectl", "get", "pod", pod_name, "-n", namespace, "-o", "json"]
            status_result = subprocess.run(status_cmd, capture_output=True, text=True)
            
            pod_status = "unknown"
            if status_result.returncode == 0:
                import json
                pod_info = json.loads(status_result.stdout)
                pod_status = pod_info.get("status", {}).get("phase", "unknown")
            
            return SuccessResult(data={
                "message": f"Successfully created pod {pod_name}",
                "pod_name": pod_name,
                "namespace": namespace,
                "project_path": project_path,
                "project_name": project_name,
                "status": pod_status,
                "port": port,
                "yaml_file": yaml_file,
                "yaml_content": yaml_content,
                "timestamp": datetime.now().isoformat()
            })
            
        except Exception as e:
            return ErrorResult(
                message=f"Unexpected error creating pod: {str(e)}",
                code="UNEXPECTED_ERROR",
                details={}
            )
    
    @classmethod
    def get_schema(cls) -> Dict[str, Any]:
        """Get JSON schema for k8s pod create command parameters."""
        return {
            "type": "object",
            "properties": {
                "project_path": {
                    "type": "string",
                    "description": "Path to project directory (defaults to current working directory)"
                },
                "image": {
                    "type": "string",
                    "description": "Docker image to use",
                    "default": "ai-admin-server:latest"
                },
                "port": {
                    "type": "integer",
                    "description": "Port to expose",
                    "default": 8060
                },
                "namespace": {
                    "type": "string",
                    "description": "Kubernetes namespace",
                    "default": "default"
                },
                "cpu_limit": {
                    "type": "string",
                    "description": "CPU limit for pod",
                    "default": "500m"
                },
                "memory_limit": {
                    "type": "string",
                    "description": "Memory limit for pod", 
                    "default": "512Mi"
                }
            }
        } 