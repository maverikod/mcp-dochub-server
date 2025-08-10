"""Kubernetes deployment creation command for MCP server."""

import os
import re
import subprocess
import yaml
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime

from mcp_proxy_adapter.commands.base import Command
from mcp_proxy_adapter.commands.result import SuccessResult, ErrorResult


class K8sDeploymentCreateCommand(Command):
    """Command to create Kubernetes deployments for projects."""
    
    name = "k8s_deployment_create"
    
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
                     replicas: int = 1,
                     cpu_limit: str = "500m",
                     memory_limit: str = "512Mi",
                     cpu_request: str = "100m",
                     memory_request: str = "128Mi",
                     **kwargs):
        """
        Create Kubernetes deployment for project with mounted directory.
        
        Args:
            project_path: Path to project directory (defaults to current working directory)
            image: Docker image to use
            port: Port to expose
            namespace: Kubernetes namespace
            replicas: Number of replicas
            cpu_limit: CPU limit for containers
            memory_limit: Memory limit for containers
            cpu_request: CPU request for containers
            memory_request: Memory request for containers
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
            deployment_name = f"ai-admin-{project_name}"
            
            # Create deployment YAML configuration
            deployment_config = {
                "apiVersion": "apps/v1",
                "kind": "Deployment",
                "metadata": {
                    "name": deployment_name,
                    "namespace": namespace,
                    "labels": {
                        "app": "ai-admin",
                        "project": project_name
                    }
                },
                "spec": {
                    "replicas": replicas,
                    "selector": {
                        "matchLabels": {
                            "app": "ai-admin",
                            "project": project_name
                        }
                    },
                    "template": {
                        "metadata": {
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
                                        "cpu": cpu_request,
                                        "memory": memory_request
                                    }
                                },
                                "env": [{
                                    "name": "PROJECT_PATH",
                                    "value": "/app"
                                }],
                                "livenessProbe": {
                                    "httpGet": {
                                        "path": "/health",
                                        "port": port
                                    },
                                    "initialDelaySeconds": 30,
                                    "periodSeconds": 10
                                },
                                "readinessProbe": {
                                    "httpGet": {
                                        "path": "/health",
                                        "port": port
                                    },
                                    "initialDelaySeconds": 5,
                                    "periodSeconds": 5
                                }
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
                }
            }
            
            # Convert to YAML
            yaml_content = yaml.dump(deployment_config, default_flow_style=False)
            
            # Save YAML to temporary file
            yaml_file = f"/tmp/{deployment_name}.yaml"
            with open(yaml_file, 'w') as f:
                f.write(yaml_content)
            
            # Check if deployment already exists
            check_cmd = ["kubectl", "get", "deployment", deployment_name, "-n", namespace]
            check_result = subprocess.run(check_cmd, capture_output=True, text=True)
            
            if check_result.returncode == 0:
                return SuccessResult(data={
                    "message": f"Deployment {deployment_name} already exists in namespace {namespace}",
                    "deployment_name": deployment_name,
                    "namespace": namespace,
                    "project_path": project_path,
                    "project_name": project_name,
                    "status": "already_exists",
                    "yaml_file": yaml_file
                })
            
            # Create the deployment
            create_cmd = ["kubectl", "apply", "-f", yaml_file]
            create_result = subprocess.run(create_cmd, capture_output=True, text=True)
            
            if create_result.returncode != 0:
                return ErrorResult(
                    message=f"Failed to create deployment: {create_result.stderr}",
                    code="DEPLOYMENT_CREATE_FAILED",
                    details={"yaml_content": yaml_content}
                )
            
            # Wait a bit and get deployment status
            import time
            time.sleep(3)
            
            status_cmd = ["kubectl", "get", "deployment", deployment_name, "-n", namespace, "-o", "json"]
            status_result = subprocess.run(status_cmd, capture_output=True, text=True)
            
            deployment_status = "unknown"
            available_replicas = 0
            if status_result.returncode == 0:
                import json
                deployment_info = json.loads(status_result.stdout)
                deployment_status = deployment_info.get("status", {})
                available_replicas = deployment_status.get("availableReplicas", 0)
            
            return SuccessResult(data={
                "message": f"Successfully created deployment {deployment_name}",
                "deployment_name": deployment_name,
                "namespace": namespace,
                "project_path": project_path,
                "project_name": project_name,
                "replicas": replicas,
                "available_replicas": available_replicas,
                "port": port,
                "yaml_file": yaml_file,
                "yaml_content": yaml_content,
                "timestamp": datetime.now().isoformat()
            })
            
        except Exception as e:
            return ErrorResult(
                message=f"Unexpected error creating deployment: {str(e)}",
                code="UNEXPECTED_ERROR",
                details={}
            )
    
    @classmethod
    def get_schema(cls) -> Dict[str, Any]:
        """Get JSON schema for k8s deployment create command parameters."""
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
                "replicas": {
                    "type": "integer",
                    "description": "Number of replicas",
                    "default": 1
                },
                "cpu_limit": {
                    "type": "string",
                    "description": "CPU limit for containers",
                    "default": "500m"
                },
                "memory_limit": {
                    "type": "string",
                    "description": "Memory limit for containers", 
                    "default": "512Mi"
                },
                "cpu_request": {
                    "type": "string",
                    "description": "CPU request for containers",
                    "default": "100m"
                },
                "memory_request": {
                    "type": "string",
                    "description": "Memory request for containers",
                    "default": "128Mi"
                }
            }
        } 