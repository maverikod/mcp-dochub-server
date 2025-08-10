"""Kubernetes namespace management commands for MCP server."""

import subprocess
import yaml
from typing import Optional, Dict, Any, List
from datetime import datetime

from mcp_proxy_adapter.commands.base import Command
from mcp_proxy_adapter.commands.result import SuccessResult, ErrorResult


class K8sNamespaceCreateCommand(Command):
    """Command to create Kubernetes namespaces."""
    
    name = "k8s_namespace_create"
    
    async def execute(self, 
                     namespace: str,
                     labels: Optional[Dict[str, str]] = None,
                     **kwargs):
        """
        Create Kubernetes namespace.
        
        Args:
            namespace: Name of namespace to create
            labels: Labels to add to namespace
        """
        try:
            # Create namespace YAML configuration
            namespace_config = {
                "apiVersion": "v1",
                "kind": "Namespace",
                "metadata": {
                    "name": namespace
                }
            }
            
            if labels:
                namespace_config["metadata"]["labels"] = labels
            
            # Convert to YAML
            yaml_content = yaml.dump(namespace_config, default_flow_style=False)
            
            # Save YAML to temporary file
            yaml_file = f"/tmp/namespace-{namespace}.yaml"
            with open(yaml_file, 'w') as f:
                f.write(yaml_content)
            
            # Check if namespace already exists
            check_cmd = ["kubectl", "get", "namespace", namespace]
            check_result = subprocess.run(check_cmd, capture_output=True, text=True)
            
            if check_result.returncode == 0:
                return SuccessResult(data={
                    "message": f"Namespace {namespace} already exists",
                    "namespace": namespace,
                    "status": "already_exists",
                    "yaml_file": yaml_file
                })
            
            # Create the namespace
            create_cmd = ["kubectl", "apply", "-f", yaml_file]
            create_result = subprocess.run(create_cmd, capture_output=True, text=True)
            
            if create_result.returncode != 0:
                return ErrorResult(
                    message=f"Failed to create namespace: {create_result.stderr}",
                    code="NAMESPACE_CREATE_FAILED",
                    details={"yaml_content": yaml_content}
                )
            
            return SuccessResult(data={
                "message": f"Successfully created namespace {namespace}",
                "namespace": namespace,
                "labels": labels or {},
                "yaml_file": yaml_file,
                "yaml_content": yaml_content,
                "timestamp": datetime.now().isoformat()
            })
            
        except Exception as e:
            return ErrorResult(
                message=f"Unexpected error creating namespace: {str(e)}",
                code="UNEXPECTED_ERROR",
                details={}
            )
    
    @classmethod
    def get_schema(cls) -> Dict[str, Any]:
        """Get JSON schema for k8s namespace create command parameters."""
        return {
            "type": "object",
            "properties": {
                "namespace": {
                    "type": "string",
                    "description": "Name of namespace to create"
                },
                "labels": {
                    "type": "object",
                    "description": "Labels to add to namespace",
                    "additionalProperties": {"type": "string"}
                }
            },
            "required": ["namespace"]
        }


class K8sNamespaceListCommand(Command):
    """Command to list Kubernetes namespaces."""
    
    name = "k8s_namespace_list"
    
    async def execute(self, **kwargs):
        """List all Kubernetes namespaces."""
        try:
            # Get all namespaces
            cmd = ["kubectl", "get", "namespaces", "-o", "json"]
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                return ErrorResult(
                    message=f"Failed to list namespaces: {result.stderr}",
                    code="KUBECTL_FAILED",
                    details={}
                )
            
            import json
            namespaces_data = json.loads(result.stdout)
            namespaces = []
            
            for ns in namespaces_data.get("items", []):
                metadata = ns.get("metadata", {})
                status = ns.get("status", {})
                
                ns_info = {
                    "name": metadata.get("name"),
                    "labels": metadata.get("labels", {}),
                    "annotations": metadata.get("annotations", {}),
                    "creation_timestamp": metadata.get("creationTimestamp"),
                    "phase": status.get("phase"),
                    "age": self._calculate_age(metadata.get("creationTimestamp"))
                }
                namespaces.append(ns_info)
            
            return SuccessResult(data={
                "message": f"Found {len(namespaces)} namespaces",
                "namespaces": namespaces,
                "timestamp": datetime.now().isoformat()
            })
            
        except Exception as e:
            return ErrorResult(
                message=f"Unexpected error listing namespaces: {str(e)}",
                code="UNEXPECTED_ERROR",
                details={}
            )
    
    def _calculate_age(self, creation_timestamp: str) -> str:
        """Calculate age of namespace from creation timestamp."""
        try:
            from datetime import datetime
            import dateutil.parser
            
            created = dateutil.parser.parse(creation_timestamp)
            now = datetime.now(created.tzinfo)
            age = now - created
            
            days = age.days
            hours, remainder = divmod(age.seconds, 3600)
            minutes, _ = divmod(remainder, 60)
            
            if days > 0:
                return f"{days}d{hours}h"
            elif hours > 0:
                return f"{hours}h{minutes}m"
            else:
                return f"{minutes}m"
                
        except Exception:
            return "unknown"
    
    @classmethod
    def get_schema(cls) -> Dict[str, Any]:
        """Get JSON schema for k8s namespace list command parameters."""
        return {
            "type": "object",
            "properties": {}
        }


class K8sNamespaceDeleteCommand(Command):
    """Command to delete Kubernetes namespaces."""
    
    name = "k8s_namespace_delete"
    
    async def execute(self, 
                     namespace: str,
                     force: bool = False,
                     **kwargs):
        """
        Delete Kubernetes namespace.
        
        Args:
            namespace: Name of namespace to delete
            force: Force delete namespace immediately
        """
        try:
            # Check if namespace exists
            check_cmd = ["kubectl", "get", "namespace", namespace]
            check_result = subprocess.run(check_cmd, capture_output=True, text=True)
            
            if check_result.returncode != 0:
                return ErrorResult(
                    message=f"Namespace {namespace} not found",
                    code="NAMESPACE_NOT_FOUND",
                    details={}
                )
            
            # Delete the namespace
            delete_cmd = ["kubectl", "delete", "namespace", namespace]
            if force:
                delete_cmd.extend(["--force", "--grace-period=0"])
            
            delete_result = subprocess.run(delete_cmd, capture_output=True, text=True)
            
            if delete_result.returncode != 0:
                return ErrorResult(
                    message=f"Failed to delete namespace: {delete_result.stderr}",
                    code="NAMESPACE_DELETE_FAILED",
                    details={}
                )
            
            return SuccessResult(data={
                "message": f"Successfully deleted namespace {namespace}",
                "namespace": namespace,
                "force": force,
                "timestamp": datetime.now().isoformat()
            })
            
        except Exception as e:
            return ErrorResult(
                message=f"Unexpected error deleting namespace: {str(e)}",
                code="UNEXPECTED_ERROR",
                details={}
            )
    
    @classmethod
    def get_schema(cls) -> Dict[str, Any]:
        """Get JSON schema for k8s namespace delete command parameters."""
        return {
            "type": "object",
            "properties": {
                "namespace": {
                    "type": "string",
                    "description": "Name of namespace to delete"
                },
                "force": {
                    "type": "boolean",
                    "description": "Force delete namespace immediately",
                    "default": False
                }
            },
            "required": ["namespace"]
        } 