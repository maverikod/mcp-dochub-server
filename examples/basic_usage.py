#!/usr/bin/env python3
"""Basic usage example for MCP Empty Server."""

import asyncio
from mcp_empty_server import create_server, run_server


def example_create_app():
    """Example of creating the FastAPI application."""
    app = create_server(
        title="My Custom Server",
        description="Example of using MCP Empty Server",
        version="1.0.0"
    )
    return app


def example_run_server():
    """Example of running the server programmatically."""
    run_server(
        host="127.0.0.1",
        port=8060,
        debug=True
    )


if __name__ == "__main__":
    # Run the server
    example_run_server() 