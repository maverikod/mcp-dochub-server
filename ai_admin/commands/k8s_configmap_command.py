"""Kubernetes ConfigMap and Secret management commands for MCP server."""

import os
import re
import subprocess
import yaml
import base64
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime

from mcp_proxy_adapter.commands.base import Command
from mcp_proxy_adapter.commands.result import SuccessResult, ErrorResult


class K8sConfigMapCreateCommand(Command):
    """Command to create Kubernetes ConfigMaps."""
    
    name = "k8s_configmap_create"
    
    def get_project_name(self, project_path: str) -> str:
        """Extract and sanitize project name from path."""
        project_name = Path(project_path).name
        # Convert to kubernetes-compatible name (lowercase, no special chars)
        sanitized = re.sub(r'[^a-z0-9]', '-', project_name.lower())
        return sanitized.strip('-')
    
    async def execute(self, 
                     configmap_name: str,
                     data: Dict[str, str],
                     namespace: str = "default",
                     project_path: Optional[str] = None,
                     labels: Optional[Dict[str, str]] = None,
                     **kwargs):
        """
        Create Kubernetes ConfigMap.
        
        Args:
            configmap_name: Name of ConfigMap
            data: Data to store in ConfigMap
            namespace: Kubernetes namespace
            project_path: Path to project directory (for labeling)
            labels: Additional labels
        """
        try:
            # Get project name for labeling
            project_name = None
            if project_path:
                project_name = self.get_project_name(project_path)
            elif not project_path:
                project_path = os.getcwd()
                project_name = self.get_project_name(project_path)
            
            # Create ConfigMap YAML configuration
            configmap_config = {
                "apiVersion": "v1",
                "kind": "ConfigMap",
                "metadata": {
                    "name": configmap_name,
                    "namespace": namespace,
                    "labels": {
                        "app": "ai-admin"
                    }
                },
                "data": data
            }
            
            if project_name:
                configmap_config["metadata"]["labels"]["project"] = project_name
            
            if labels:
                configmap_config["metadata"]["labels"].update(labels)
            
            # Convert to YAML
            yaml_content = yaml.dump(configmap_config, default_flow_style=False)
            
            # Save YAML to temporary file
            yaml_file = f"/tmp/configmap-{configmap_name}.yaml"
            with open(yaml_file, 'w') as f:
                f.write(yaml_content)
            
            # Check if ConfigMap already exists
            check_cmd = ["kubectl", "get", "configmap", configmap_name, "-n", namespace]
            check_result = subprocess.run(check_cmd, capture_output=True, text=True)
            
            if check_result.returncode == 0:
                return SuccessResult(data={
                    "message": f"ConfigMap {configmap_name} already exists in namespace {namespace}",
                    "configmap_name": configmap_name,
                    "namespace": namespace,
                    "status": "already_exists",
                    "yaml_file": yaml_file
                })
            
            # Create the ConfigMap
            create_cmd = ["kubectl", "apply", "-f", yaml_file]
            create_result = subprocess.run(create_cmd, capture_output=True, text=True)
            
            if create_result.returncode != 0:
                return ErrorResult(
                    message=f"Failed to create ConfigMap: {create_result.stderr}",
                    code="CONFIGMAP_CREATE_FAILED",
                    details={"yaml_content": yaml_content}
                )
            
            return SuccessResult(data={
                "message": f"Successfully created ConfigMap {configmap_name}",
                "configmap_name": configmap_name,
                "namespace": namespace,
                "data": data,
                "labels": configmap_config["metadata"]["labels"],
                "yaml_file": yaml_file,
                "yaml_content": yaml_content,
                "timestamp": datetime.now().isoformat()
            })
            
        except Exception as e:
            return ErrorResult(
                message=f"Unexpected error creating ConfigMap: {str(e)}",
                code="UNEXPECTED_ERROR",
                details={}
            )
    
    @classmethod
    def get_schema(cls) -> Dict[str, Any]:
        """Get JSON schema for k8s configmap create command parameters."""
        return {
            "type": "object",
            "properties": {
                "configmap_name": {
                    "type": "string",
                    "description": "Name of ConfigMap"
                },
                "data": {
                    "type": "object",
                    "description": "Data to store in ConfigMap",
                    "additionalProperties": {"type": "string"}
                },
                "namespace": {
                    "type": "string",
                    "description": "Kubernetes namespace",
                    "default": "default"
                },
                "project_path": {
                    "type": "string",
                    "description": "Path to project directory (for labeling)"
                },
                "labels": {
                    "type": "object",
                    "description": "Additional labels",
                    "additionalProperties": {"type": "string"}
                }
            },
            "required": ["configmap_name", "data"]
        }


class K8sSecretCreateCommand(Command):
    """Command to create Kubernetes Secrets."""
    
    name = "k8s_secret_create"
    
    def get_project_name(self, project_path: str) -> str:
        """Extract and sanitize project name from path."""
        project_name = Path(project_path).name
        # Convert to kubernetes-compatible name (lowercase, no special chars)
        sanitized = re.sub(r'[^a-z0-9]', '-', project_name.lower())
        return sanitized.strip('-')
    
    async def execute(self, 
                     secret_name: str,
                     data: Dict[str, str],
                     secret_type: str = "Opaque",
                     namespace: str = "default",
                     project_path: Optional[str] = None,
                     labels: Optional[Dict[str, str]] = None,
                     **kwargs):
        """
        Create Kubernetes Secret.
        
        Args:
            secret_name: Name of Secret
            data: Data to store in Secret (will be base64 encoded)
            secret_type: Type of Secret (Opaque, kubernetes.io/tls, etc.)
            namespace: Kubernetes namespace
            project_path: Path to project directory (for labeling)
            labels: Additional labels
        """
        try:
            # Get project name for labeling
            project_name = None
            if project_path:
                project_name = self.get_project_name(project_path)
            elif not project_path:
                project_path = os.getcwd()
                project_name = self.get_project_name(project_path)
            
            # Encode data to base64
            encoded_data = {}
            for key, value in data.items():
                encoded_data[key] = base64.b64encode(value.encode('utf-8')).decode('utf-8')
            
            # Create Secret YAML configuration
            secret_config = {
                "apiVersion": "v1",
                "kind": "Secret",
                "metadata": {
                    "name": secret_name,
                    "namespace": namespace,
                    "labels": {
                        "app": "ai-admin"
                    }
                },
                "type": secret_type,
                "data": encoded_data
            }
            
            if project_name:
                secret_config["metadata"]["labels"]["project"] = project_name
            
            if labels:
                secret_config["metadata"]["labels"].update(labels)
            
            # Convert to YAML
            yaml_content = yaml.dump(secret_config, default_flow_style=False)
            
            # Save YAML to temporary file
            yaml_file = f"/tmp/secret-{secret_name}.yaml"
            with open(yaml_file, 'w') as f:
                f.write(yaml_content)
            
            # Check if Secret already exists
            check_cmd = ["kubectl", "get", "secret", secret_name, "-n", namespace]
            check_result = subprocess.run(check_cmd, capture_output=True, text=True)
            
            if check_result.returncode == 0:
                return SuccessResult(data={
                    "message": f"Secret {secret_name} already exists in namespace {namespace}",
                    "secret_name": secret_name,
                    "namespace": namespace,
                    "status": "already_exists",
                    "yaml_file": yaml_file
                })
            
            # Create the Secret
            create_cmd = ["kubectl", "apply", "-f", yaml_file]
            create_result = subprocess.run(create_cmd, capture_output=True, text=True)
            
            if create_result.returncode != 0:
                return ErrorResult(
                    message=f"Failed to create Secret: {create_result.stderr}",
                    code="SECRET_CREATE_FAILED",
                    details={}
                )
            
            return SuccessResult(data={
                "message": f"Successfully created Secret {secret_name}",
                "secret_name": secret_name,
                "namespace": namespace,
                "secret_type": secret_type,
                "data_keys": list(data.keys()),  # Don't expose actual data
                "labels": secret_config["metadata"]["labels"],
                "yaml_file": yaml_file,
                "timestamp": datetime.now().isoformat()
            })
            
        except Exception as e:
            return ErrorResult(
                message=f"Unexpected error creating Secret: {str(e)}",
                code="UNEXPECTED_ERROR",
                details={}
            )
    
    @classmethod
    def get_schema(cls) -> Dict[str, Any]:
        """Get JSON schema for k8s secret create command parameters."""
        return {
            "type": "object",
            "properties": {
                "secret_name": {
                    "type": "string",
                    "description": "Name of Secret"
                },
                "data": {
                    "type": "object",
                    "description": "Data to store in Secret (will be base64 encoded)",
                    "additionalProperties": {"type": "string"}
                },
                "secret_type": {
                    "type": "string",
                    "description": "Type of Secret",
                    "default": "Opaque",
                    "enum": ["Opaque", "kubernetes.io/tls", "kubernetes.io/dockerconfigjson"]
                },
                "namespace": {
                    "type": "string",
                    "description": "Kubernetes namespace",
                    "default": "default"
                },
                "project_path": {
                    "type": "string",
                    "description": "Path to project directory (for labeling)"
                },
                "labels": {
                    "type": "object",
                    "description": "Additional labels",
                    "additionalProperties": {"type": "string"}
                }
            },
            "required": ["secret_name", "data"]
        }


class K8sResourceDeleteCommand(Command):
    """Command to delete Kubernetes resources."""
    
    name = "k8s_resource_delete"
    
    async def execute(self, 
                     resource_type: str,
                     resource_name: str,
                     namespace: str = "default",
                     force: bool = False,
                     **kwargs):
        """
        Delete Kubernetes resource.
        
        Args:
            resource_type: Type of resource (pod, deployment, service, configmap, secret, etc.)
            resource_name: Name of resource to delete
            namespace: Kubernetes namespace
            force: Force delete resource immediately
        """
        try:
            # Check if resource exists
            check_cmd = ["kubectl", "get", resource_type, resource_name, "-n", namespace]
            check_result = subprocess.run(check_cmd, capture_output=True, text=True)
            
            if check_result.returncode != 0:
                return ErrorResult(
                    message=f"{resource_type} {resource_name} not found in namespace {namespace}",
                    code="RESOURCE_NOT_FOUND",
                    details={}
                )
            
            # Delete the resource
            delete_cmd = ["kubectl", "delete", resource_type, resource_name, "-n", namespace]
            if force:
                delete_cmd.extend(["--force", "--grace-period=0"])
            
            delete_result = subprocess.run(delete_cmd, capture_output=True, text=True)
            
            if delete_result.returncode != 0:
                return ErrorResult(
                    message=f"Failed to delete {resource_type}: {delete_result.stderr}",
                    code="RESOURCE_DELETE_FAILED",
                    details={}
                )
            
            return SuccessResult(data={
                "message": f"Successfully deleted {resource_type} {resource_name}",
                "resource_type": resource_type,
                "resource_name": resource_name,
                "namespace": namespace,
                "force": force,
                "timestamp": datetime.now().isoformat()
            })
            
        except Exception as e:
            return ErrorResult(
                message=f"Unexpected error deleting resource: {str(e)}",
                code="UNEXPECTED_ERROR",
                details={}
            )
    
    @classmethod
    def get_schema(cls) -> Dict[str, Any]:
        """Get JSON schema for k8s resource delete command parameters."""
        return {
            "type": "object",
            "properties": {
                "resource_type": {
                    "type": "string",
                    "description": "Type of resource",
                    "enum": ["pod", "deployment", "service", "configmap", "secret", "namespace", "ingress", "pvc"]
                },
                "resource_name": {
                    "type": "string",
                    "description": "Name of resource to delete"
                },
                "namespace": {
                    "type": "string",
                    "description": "Kubernetes namespace",
                    "default": "default"
                },
                "force": {
                    "type": "boolean",
                    "description": "Force delete resource immediately",
                    "default": False
                }
            },
            "required": ["resource_type", "resource_name"]
        } 