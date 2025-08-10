"""Main server implementation with command autodiscovery."""

import os
import logging
from typing import Optional, Dict, Any
import uvicorn
from mcp_proxy_adapter import create_app
from mcp_proxy_adapter.core.logging import get_logger, setup_logging
from mcp_proxy_adapter.config import config

from ai_admin.commands.registry import command_registry
from ai_admin.version import __version__


def create_server(
    title: str = "AI Admin - MCP Server",
    description: str = "AI Admin server with command autodiscovery support to manage DockerHub, GitHub, Vast.ai GPU instances, and Kubernetes resources",
    version: str = __version__,
    config_path: Optional[str] = None
) -> Any:
    """Create FastAPI application with autodiscovered commands.
    
    Args:
        title: Server title
        description: Server description
        version: Server version
        config_path: Path to configuration file (defaults to config/config.json)
        
    Returns:
        FastAPI application instance
    """
    # Set default config path if not provided
    if config_path is None:
        config_path = "config/config.json"
    
    # Load configuration if file exists
    if os.path.exists(config_path):
        config.load_from_file(config_path)
        logging.info(f"Loaded configuration from: {config_path}")
    else:
        logging.warning(f"Configuration file not found: {config_path}")
    
    # Setup logging
    setup_logging()
    logger = get_logger("ai_admin")
    
    # Discover and register commands from our package
    logger.info("Starting command autodiscovery...")
    command_registry.discover_commands("ai_admin.commands")
    
    # Get command count
    all_commands = command_registry.get_all_commands()
    logger.info(f"Total commands available: {len(all_commands)}")
    
    # Create FastAPI application
    app = create_app(
        title=title,
        description=description,
        version=version
    )
    
    return app


def run_server(
    host: str = "0.0.0.0",
    port: int = 8060,
    debug: bool = False,
    config_path: Optional[str] = None,
    **server_kwargs
) -> None:
    """Run the server with specified parameters.
    
    Args:
        host: Server host
        port: Server port
        debug: Debug mode
        config_path: Path to configuration file
        **server_kwargs: Additional uvicorn parameters
    """
    # Create application
    app = create_server(config_path=config_path)
    
    # Get logger
    logger = get_logger("ai_admin")
    
    # Print server information
    print("=" * 80)
    print("🚀 AI ADMIN")
    print("=" * 80)
    print(f"📋 Description: AI Admin with command autodiscovery")
    print(f"🔧 Version: {__version__}")
    print()
    print("⚙️  Configuration:")
    print(f"   • Server: {host}:{port}")
    print(f"   • Debug: {debug}")
    print()
    
    # Get command information
    all_commands = command_registry.get_all_commands()
    print(f"🔧 Available Commands ({len(all_commands)}):")
    for cmd_name in sorted(all_commands.keys()):
        cmd_class = all_commands[cmd_name]
        cmd_doc = cmd_class.__doc__ or "No description"
        # Get first line of docstring
        summary = cmd_doc.split('\n')[0].strip()
        print(f"   • {cmd_name} - {summary}")
    print()
    
    print("🎯 Features:")
    print("   • Automatic command discovery")
    print("   • Standard JSON-RPC API")
    print("   • Built-in logging and error handling")
    print("   • OpenAPI schema generation")
    print("   • Configuration support")
    print("=" * 80)
    print()
    
    logger.info(f"Starting AI Admin on {host}:{port}")
    
    # Run server
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="debug" if debug else "info",
        **server_kwargs
    )


def main() -> None:
    """Main entry point for command line usage."""
    import argparse
    
    parser = argparse.ArgumentParser(description="AI Admin")
    parser.add_argument("--host", default="0.0.0.0", help="Server host")
    parser.add_argument("--port", type=int, default=8060, help="Server port")
    parser.add_argument("--debug", action="store_true", help="Debug mode")
    parser.add_argument("--config", help="Configuration file path")
    
    args = parser.parse_args()
    
    run_server(
        host=args.host,
        port=args.port,
        debug=args.debug,
        config_path=args.config
    )


if __name__ == "__main__":
    main() 