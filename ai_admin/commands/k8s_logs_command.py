"""Kubernetes logs and monitoring commands for MCP server."""

import os
import re
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime

from mcp_proxy_adapter.commands.base import Command
from mcp_proxy_adapter.commands.result import SuccessResult, ErrorResult


class K8sLogsCommand(Command):
    """Command to get Kubernetes pod logs."""
    
    name = "k8s_logs"
    
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
                     container: Optional[str] = None,
                     lines: int = 100,
                     follow: bool = False,
                     previous: bool = False,
                     since: Optional[str] = None,
                     **kwargs):
        """
        Get logs from Kubernetes pods.
        
        Args:
            pod_name: Name of pod (if not provided, derived from project_path)
            project_path: Path to project directory (used to derive pod name)
            namespace: Kubernetes namespace
            container: Container name (if pod has multiple containers)
            lines: Number of lines to retrieve
            follow: Follow log output
            previous: Get logs from previous container instance
            since: Show logs since time (e.g., '1h', '30m', '2006-01-02T15:04:05Z')
        """
        try:
            # Determine pod name
            if not pod_name:
                if not project_path:
                    project_path = os.getcwd()
                
                project_name = self.get_project_name(project_path)
                
                # Try to find pod by project label
                find_cmd = [
                    "kubectl", "get", "pods", "-n", namespace,
                    "-l", f"project={project_name}",
                    "-o", "jsonpath={.items[0].metadata.name}"
                ]
                find_result = subprocess.run(find_cmd, capture_output=True, text=True)
                
                if find_result.returncode == 0 and find_result.stdout.strip():
                    pod_name = find_result.stdout.strip()
                else:
                    pod_name = f"ai-admin-{project_name}"
            
            # Build kubectl logs command
            logs_cmd = ["kubectl", "logs", pod_name, "-n", namespace]
            
            if container:
                logs_cmd.extend(["-c", container])
            
            if lines > 0:
                logs_cmd.extend(["--tail", str(lines)])
            
            if follow:
                logs_cmd.append("--follow")
            
            if previous:
                logs_cmd.append("--previous")
            
            if since:
                logs_cmd.extend(["--since", since])
            
            # Execute logs command
            logs_result = subprocess.run(logs_cmd, capture_output=True, text=True)
            
            if logs_result.returncode != 0:
                return ErrorResult(
                    message=f"Failed to get logs: {logs_result.stderr}",
                    code="LOGS_FAILED",
                    details={}
                )
            
            return SuccessResult(data={
                "message": f"Retrieved logs from pod {pod_name}",
                "pod_name": pod_name,
                "namespace": namespace,
                "container": container,
                "lines": lines,
                "logs": logs_result.stdout,
                "timestamp": datetime.now().isoformat()
            })
            
        except Exception as e:
            return ErrorResult(
                message=f"Unexpected error getting logs: {str(e)}",
                code="UNEXPECTED_ERROR",
                details={}
            )
    
    @classmethod
    def get_schema(cls) -> Dict[str, Any]:
        """Get JSON schema for k8s logs command parameters."""
        return {
            "type": "object",
            "properties": {
                "pod_name": {
                    "type": "string",
                    "description": "Name of pod (if not provided, derived from project_path)"
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
                "container": {
                    "type": "string",
                    "description": "Container name (if pod has multiple containers)"
                },
                "lines": {
                    "type": "integer",
                    "description": "Number of lines to retrieve",
                    "default": 100,
                    "minimum": 1
                },
                "follow": {
                    "type": "boolean",
                    "description": "Follow log output",
                    "default": False
                },
                "previous": {
                    "type": "boolean",
                    "description": "Get logs from previous container instance",
                    "default": False
                },
                "since": {
                    "type": "string",
                    "description": "Show logs since time (e.g., '1h', '30m', '2006-01-02T15:04:05Z')"
                }
            }
        }


class K8sExecCommand(Command):
    """Command to execute commands in Kubernetes pods."""
    
    name = "k8s_exec"
    
    def get_project_name(self, project_path: str) -> str:
        """Extract and sanitize project name from path."""
        project_name = Path(project_path).name
        # Convert to kubernetes-compatible name (lowercase, no special chars)
        sanitized = re.sub(r'[^a-z0-9]', '-', project_name.lower())
        return sanitized.strip('-')
    
    async def execute(self, 
                     command: str,
                     pod_name: Optional[str] = None,
                     project_path: Optional[str] = None,
                     namespace: str = "default",
                     container: Optional[str] = None,
                     interactive: bool = False,
                     tty: bool = False,
                     **kwargs):
        """
        Execute command in Kubernetes pod.
        
        Args:
            command: Command to execute
            pod_name: Name of pod (if not provided, derived from project_path)
            project_path: Path to project directory (used to derive pod name)
            namespace: Kubernetes namespace
            container: Container name (if pod has multiple containers)
            interactive: Keep STDIN open
            tty: Allocate a TTY
        """
        try:
            # Determine pod name
            if not pod_name:
                if not project_path:
                    project_path = os.getcwd()
                
                project_name = self.get_project_name(project_path)
                
                # Try to find pod by project label
                find_cmd = [
                    "kubectl", "get", "pods", "-n", namespace,
                    "-l", f"project={project_name}",
                    "-o", "jsonpath={.items[0].metadata.name}"
                ]
                find_result = subprocess.run(find_cmd, capture_output=True, text=True)
                
                if find_result.returncode == 0 and find_result.stdout.strip():
                    pod_name = find_result.stdout.strip()
                else:
                    pod_name = f"ai-admin-{project_name}"
            
            # Build kubectl exec command
            exec_cmd = ["kubectl", "exec", pod_name, "-n", namespace]
            
            if container:
                exec_cmd.extend(["-c", container])
            
            if interactive:
                exec_cmd.append("-i")
            
            if tty:
                exec_cmd.append("-t")
            
            exec_cmd.append("--")
            exec_cmd.extend(command.split())
            
            # Execute command
            exec_result = subprocess.run(exec_cmd, capture_output=True, text=True)
            
            return SuccessResult(data={
                "message": f"Executed command in pod {pod_name}",
                "pod_name": pod_name,
                "namespace": namespace,
                "container": container,
                "command": command,
                "exit_code": exec_result.returncode,
                "stdout": exec_result.stdout,
                "stderr": exec_result.stderr,
                "timestamp": datetime.now().isoformat()
            })
            
        except Exception as e:
            return ErrorResult(
                message=f"Unexpected error executing command: {str(e)}",
                code="UNEXPECTED_ERROR",
                details={}
            )
    
    @classmethod
    def get_schema(cls) -> Dict[str, Any]:
        """Get JSON schema for k8s exec command parameters."""
        return {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "Command to execute"
                },
                "pod_name": {
                    "type": "string",
                    "description": "Name of pod (if not provided, derived from project_path)"
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
                "container": {
                    "type": "string",
                    "description": "Container name (if pod has multiple containers)"
                },
                "interactive": {
                    "type": "boolean",
                    "description": "Keep STDIN open",
                    "default": False
                },
                "tty": {
                    "type": "boolean",
                    "description": "Allocate a TTY",
                    "default": False
                }
            },
            "required": ["command"]
        }


class K8sPortForwardCommand(Command):
    """Command to setup port forwarding to Kubernetes pods."""
    
    name = "k8s_port_forward"
    
    def get_project_name(self, project_path: str) -> str:
        """Extract and sanitize project name from path."""
        project_name = Path(project_path).name
        # Convert to kubernetes-compatible name (lowercase, no special chars)
        sanitized = re.sub(r'[^a-z0-9]', '-', project_name.lower())
        return sanitized.strip('-')
    
    async def execute(self, 
                     local_port: int,
                     remote_port: int,
                     pod_name: Optional[str] = None,
                     project_path: Optional[str] = None,
                     namespace: str = "default",
                     background: bool = True,
                     **kwargs):
        """
        Setup port forwarding to Kubernetes pod.
        
        Args:
            local_port: Local port to forward from
            remote_port: Remote port on pod to forward to
            pod_name: Name of pod (if not provided, derived from project_path)
            project_path: Path to project directory (used to derive pod name)
            namespace: Kubernetes namespace
            background: Run port forwarding in background
        """
        try:
            # Determine pod name
            if not pod_name:
                if not project_path:
                    project_path = os.getcwd()
                
                project_name = self.get_project_name(project_path)
                
                # Try to find pod by project label
                find_cmd = [
                    "kubectl", "get", "pods", "-n", namespace,
                    "-l", f"project={project_name}",
                    "-o", "jsonpath={.items[0].metadata.name}"
                ]
                find_result = subprocess.run(find_cmd, capture_output=True, text=True)
                
                if find_result.returncode == 0 and find_result.stdout.strip():
                    pod_name = find_result.stdout.strip()
                else:
                    pod_name = f"ai-admin-{project_name}"
            
            # Build kubectl port-forward command
            port_forward_cmd = [
                "kubectl", "port-forward", pod_name,
                f"{local_port}:{remote_port}",
                "-n", namespace
            ]
            
            if background:
                # Start port forwarding in background
                import subprocess
                process = subprocess.Popen(
                    port_forward_cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                
                # Give it a moment to start
                import time
                time.sleep(2)
                
                # Check if process is still running
                if process.poll() is None:
                    return SuccessResult(data={
                        "message": f"Port forwarding started: localhost:{local_port} -> {pod_name}:{remote_port}",
                        "pod_name": pod_name,
                        "namespace": namespace,
                        "local_port": local_port,
                        "remote_port": remote_port,
                        "process_id": process.pid,
                        "background": background,
                        "access_url": f"http://localhost:{local_port}",
                        "timestamp": datetime.now().isoformat()
                    })
                else:
                    stdout, stderr = process.communicate()
                    return ErrorResult(
                        message=f"Port forwarding failed: {stderr}",
                        code="PORT_FORWARD_FAILED",
                        details={"stdout": stdout, "stderr": stderr}
                    )
            else:
                # Run port forwarding synchronously (blocking)
                port_forward_result = subprocess.run(port_forward_cmd, capture_output=True, text=True)
                
                return SuccessResult(data={
                    "message": f"Port forwarding completed",
                    "pod_name": pod_name,
                    "namespace": namespace,
                    "local_port": local_port,
                    "remote_port": remote_port,
                    "exit_code": port_forward_result.returncode,
                    "stdout": port_forward_result.stdout,
                    "stderr": port_forward_result.stderr,
                    "timestamp": datetime.now().isoformat()
                })
            
        except Exception as e:
            return ErrorResult(
                message=f"Unexpected error setting up port forwarding: {str(e)}",
                code="UNEXPECTED_ERROR",
                details={}
            )
    
    @classmethod
    def get_schema(cls) -> Dict[str, Any]:
        """Get JSON schema for k8s port forward command parameters."""
        return {
            "type": "object",
            "properties": {
                "local_port": {
                    "type": "integer",
                    "description": "Local port to forward from",
                    "minimum": 1,
                    "maximum": 65535
                },
                "remote_port": {
                    "type": "integer",
                    "description": "Remote port on pod to forward to",
                    "minimum": 1,
                    "maximum": 65535
                },
                "pod_name": {
                    "type": "string",
                    "description": "Name of pod (if not provided, derived from project_path)"
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
                "background": {
                    "type": "boolean",
                    "description": "Run port forwarding in background",
                    "default": True
                }
            },
            "required": ["local_port", "remote_port"]
        } 