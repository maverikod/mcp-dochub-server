"""Example command to demonstrate autodiscovery."""

from typing import Dict, Any
from datetime import datetime
from mcp_proxy_adapter.commands.base import Command
from mcp_proxy_adapter.commands.result import SuccessResult


class ExampleCommand(Command):
    """Example command to demonstrate autodiscovery.
    
    This is a simple example command that demonstrates how commands
    are automatically discovered and registered by the server.
    """
    
    name = "example"
    
    async def execute(self, message: str = "Hello from MCP Empty Server!") -> SuccessResult:
        """Execute example command.
        
        Args:
            message: Message to return
            
        Returns:
            Success result with the message
        """
        return SuccessResult(data={
            "message": message,
            "server": "MCP Empty Server",
            "command": self.name,
            "timestamp": datetime.now().isoformat()
        })
    
    @classmethod
    def get_schema(cls) -> Dict[str, Any]:
        """Get JSON schema for example command parameters."""
        return {
            "type": "object",
            "properties": {
                "message": {
                    "type": "string",
                    "description": "Message to return",
                    "default": "Hello from MCP Empty Server!"
                }
            },
            "additionalProperties": False
        } 