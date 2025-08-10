"""AI Admin - AI Admin with command autodiscovery support.

This package provides a minimal server implementation using mcp_proxy_adapter
framework with automatic command discovery capabilities.
"""

from ai_admin.version import __version__
from ai_admin.server import create_server, run_server
from ai_admin.commands.base import EmptyCommand
from ai_admin.commands.registry import command_registry

__all__ = [
    "__version__",
    "create_server", 
    "run_server",
    "EmptyCommand",
    "command_registry"
] 