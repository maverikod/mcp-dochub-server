"""Commands module for MCP Empty Server."""

from mcp_empty_server.commands.base import EmptyCommand
from mcp_empty_server.commands.registry import command_registry

__all__ = ["EmptyCommand", "command_registry"] 