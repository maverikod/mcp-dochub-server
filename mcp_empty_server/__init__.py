"""MCP Empty Server - Empty server with command autodiscovery support.

This package provides a minimal server implementation using mcp_proxy_adapter
framework with automatic command discovery capabilities.
"""

from mcp_empty_server.version import __version__
from mcp_empty_server.server import create_server, run_server
from mcp_empty_server.commands.base import EmptyCommand
from mcp_empty_server.commands.registry import command_registry

__all__ = [
    "__version__",
    "create_server", 
    "run_server",
    "EmptyCommand",
    "command_registry"
] 