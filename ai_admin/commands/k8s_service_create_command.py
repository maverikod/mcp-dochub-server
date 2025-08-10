"""Kubernetes service creation command for MCP server."""

import os
import re
import subprocess
import yaml
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime

from mcp_proxy_adapter.commands.base import Command
from mcp_proxy_adapter.commands.result import SuccessResult, ErrorResult


class K8sServiceCreateCommand(Command):
    """Command to create Kubernetes services for projects."""
    
    name = "k8s_service_create"
    
    def get_project_name(self, project_path: str) -> str:
        """Extract and sanitize project name from path."""
        project_name = Path(project_path).name
        # Convert to kubernetes-compatible name (lowercase, no special chars)
        sanitized = re.sub(r'[^a-z0-9]', '-', project_name.lower())
        return sanitized.strip('-')
    
    async def execute(self, 
                     project_path: Optional[str] = None,
                     service_type: str = "ClusterIP",
                     port: int = 8060,
                     target_port: int = 8060,
                     node_port: Optional[int] = None,
                     namespace: str = "default",
                     **kwargs):
        """
        Create Kubernetes service for project deployment.
        
        Args:
            project_path: Path to project directory (defaults to current working directory)
            service_type: Type of service (ClusterIP, NodePort, LoadBalancer)
            port: Service port
            target_port: Target port on pods
            node_port: NodePort (only for NodePort service type)
            namespace: Kubernetes namespace
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
            service_name = f"ai-admin-{project_name}-service"
            
            # Create service YAML configuration
            service_config = {
                "apiVersion": "v1",
                "kind": "Service",
                "metadata": {
                    "name": service_name,
                    "namespace": namespace,
                    "labels": {
                        "app": "ai-admin",
                        "project": project_name
                    }
                },
                "spec": {
                    "type": service_type,
                    "selector": {
                        "app": "ai-admin",
                        "project": project_name
                    },
                    "ports": [{
                        "port": port,
                        "targetPort": target_port,
                        "protocol": "TCP",
                        "name": "http"
                    }]
                }
            }
            
            # Add nodePort for NodePort service type
            if service_type == "NodePort" and node_port:
                service_config["spec"]["ports"][0]["nodePort"] = node_port
            
            # Convert to YAML
            yaml_content = yaml.dump(service_config, default_flow_style=False)
            
            # Save YAML to temporary file
            yaml_file = f"/tmp/{service_name}.yaml"
            with open(yaml_file, 'w') as f:
                f.write(yaml_content)
            
            # Check if service already exists
            check_cmd = ["kubectl", "get", "service", service_name, "-n", namespace]
            check_result = subprocess.run(check_cmd, capture_output=True, text=True)
            
            if check_result.returncode == 0:
                return SuccessResult(data={
                    "message": f"Service {service_name} already exists in namespace {namespace}",
                    "service_name": service_name,
                    "namespace": namespace,
                    "project_path": project_path,
                    "project_name": project_name,
                    "service_type": service_type,
                    "status": "already_exists",
                    "yaml_file": yaml_file
                })
            
            # Create the service
            create_cmd = ["kubectl", "apply", "-f", yaml_file]
            create_result = subprocess.run(create_cmd, capture_output=True, text=True)
            
            if create_result.returncode != 0:
                return ErrorResult(
                    message=f"Failed to create service: {create_result.stderr}",
                    code="SERVICE_CREATE_FAILED",
                    details={"yaml_content": yaml_content}
                )
            
            # Get service status
            status_cmd = ["kubectl", "get", "service", service_name, "-n", namespace, "-o", "json"]
            status_result = subprocess.run(status_cmd, capture_output=True, text=True)
            
            service_info = {}
            if status_result.returncode == 0:
                import json
                service_data = json.loads(status_result.stdout)
                service_info = {
                    "cluster_ip": service_data.get("spec", {}).get("clusterIP"),
                    "external_ips": service_data.get("spec", {}).get("externalIPs", []),
                    "ports": service_data.get("spec", {}).get("ports", [])
                }
                
                # Add load balancer info if applicable
                if service_type == "LoadBalancer":
                    ingress = service_data.get("status", {}).get("loadBalancer", {}).get("ingress", [])
                    service_info["load_balancer_ingress"] = ingress
            
            return SuccessResult(data={
                "message": f"Successfully created service {service_name}",
                "service_name": service_name,
                "namespace": namespace,
                "project_path": project_path,
                "project_name": project_name,
                "service_type": service_type,
                "port": port,
                "target_port": target_port,
                "node_port": node_port,
                "service_info": service_info,
                "yaml_file": yaml_file,
                "yaml_content": yaml_content,
                "timestamp": datetime.now().isoformat()
            })
            
        except Exception as e:
            return ErrorResult(
                message=f"Unexpected error creating service: {str(e)}",
                code="UNEXPECTED_ERROR",
                details={}
            )
    
    @classmethod
    def get_schema(cls) -> Dict[str, Any]:
        """Get JSON schema for k8s service create command parameters."""
        return {
            "type": "object",
            "properties": {
                "project_path": {
                    "type": "string",
                    "description": "Path to project directory (defaults to current working directory)"
                },
                "service_type": {
                    "type": "string",
                    "description": "Type of service",
                    "enum": ["ClusterIP", "NodePort", "LoadBalancer"],
                    "default": "ClusterIP"
                },
                "port": {
                    "type": "integer",
                    "description": "Service port",
                    "default": 8060
                },
                "target_port": {
                    "type": "integer", 
                    "description": "Target port on pods",
                    "default": 8060
                },
                "node_port": {
                    "type": "integer",
                    "description": "NodePort (only for NodePort service type)",
                    "minimum": 30000,
                    "maximum": 32767
                },
                "namespace": {
                    "type": "string",
                    "description": "Kubernetes namespace",
                    "default": "default"
                }
            }
        } 