# MCP Empty Server

Empty server with command autodiscovery support using mcp_proxy_adapter framework.

## Features

- **Automatic Command Discovery**: Commands are automatically discovered and registered
- **Standard JSON-RPC API**: Compatible with mcp_proxy_adapter JSON-RPC protocol
- **Built-in Commands**: Includes help, health, config, and reload commands
- **OpenAPI Schema**: Automatic API documentation generation
- **Configuration Support**: Flexible configuration through files and environment variables
- **Extensible**: Easy to add custom commands

## Installation

```bash
pip install mcp-empty-server
```

## Quick Start

### Command Line Usage

Start the server with default settings:

```bash
mcp-empty-server
```

With custom configuration:

```bash
mcp-empty-server --host 127.0.0.1 --port 8080 --config config.json
```

### Programmatic Usage

```python
from mcp_empty_server import create_server, run_server

# Create application
app = create_server(
    title="My Custom Server",
    description="My custom server description",
    version="1.0.0"
)

# Or run directly
run_server(
    host="0.0.0.0",
    port=8060,
    debug=True
)
```

## Adding Custom Commands

Create a command file with `_command.py` suffix in the `mcp_empty_server/commands/` directory:

```python
# my_custom_command.py
from typing import Dict, Any
from mcp_proxy_adapter.commands.base import Command
from mcp_proxy_adapter.commands.result import SuccessResult

class MyCustomCommand(Command):
    """My custom command description."""
    
    name = "my_custom"
    
    async def execute(self, param1: str = "default") -> SuccessResult:
        """Execute my custom command.
        
        Args:
            param1: First parameter
            
        Returns:
            Success result
        """
        return SuccessResult(data={
            "result": f"Hello {param1}!",
            "command": self.name
        })
    
    @classmethod
    def get_schema(cls) -> Dict[str, Any]:
        """Get command schema."""
        return {
            "type": "object",
            "properties": {
                "param1": {
                    "type": "string",
                    "description": "First parameter",
                    "default": "default"
                }
            }
        }
```

The command will be automatically discovered and available via JSON-RPC:

```bash
curl -X POST http://localhost:8060/cmd \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc": "2.0", "method": "my_custom", "params": {"param1": "world"}, "id": 1}'
```

## Built-in Commands

- `help` - List all available commands
- `health` - Server health check
- `config` - Get server configuration
- `reload` - Reload server configuration and commands
- `example` - Example command demonstrating the server

## Docker Commands

- `docker_login` - Authenticate with Docker registries
- `docker_build` - Build Docker images from Dockerfile
- `docker_tag` - Tag Docker images with new names
- `docker_push` - Push Docker images to registries
- `docker_images` - List local Docker images
- `docker_rmi` - Remove Docker images

## GitHub Commands

- `github_create_repo` - Create new GitHub repository via API
- `github_list_repos` - List your GitHub repositories
- `git_clone` - Clone Git repositories locally

## Git Commands (Local Repository)

- `git_init` - Initialize Git repository
- `git_status` - Get repository status and file changes
- `git_commit` - Create commits with file staging
- `git_push` - Push changes to remote repository

## Vast.ai Commands (GPU Cloud Computing)

- `vast_search` - Search for available GPU instances
- `vast_create` - Create (rent) GPU instances
- `vast_instances` - List your active instances
- `vast_destroy` - Stop/delete GPU instances

## Queue Commands

- `queue_status` - Get overall queue status
- `queue_task_status` - Get specific task status
- `queue_push` - Add Docker push task to queue
- `queue_cancel` - Cancel a queued task

## Configuration

Create a `config.json` file:

```json
{
  "server": {
    "host": "0.0.0.0",
    "port": 8060,
    "debug": false,
    "log_level": "INFO"
  },
  "logging": {
    "level": "INFO",
    "file_output": true,
    "log_dir": "./logs"
  },
  "commands": {
    "auto_discovery": true,
    "discovery_path": "mcp_empty_server.commands"
  },
  "docker": {
    "username": "your-docker-username",
    "token": "your-docker-access-token",
    "registry": "docker.io"
  },
  "github": {
    "username": "your-github-username", 
    "token": "ghp_your_personal_access_token_here"
  },
  "vast": {
    "api_key": "your-vast-api-key-here",
    "api_url": "https://console.vast.ai/api/v0"
  }
}
```

### Getting API Keys

- **Docker**: Create access token at [Docker Hub Settings](https://hub.docker.com/settings/security)
- **GitHub**: Create PAT at [GitHub Settings > Developer settings > Personal access tokens](https://github.com/settings/tokens)
- **Vast.ai**: Get API key from [Vast.ai Console > Account](https://console.vast.ai/account/)

## API Documentation

Once the server is running, visit:
- OpenAPI docs: `http://localhost:8060/docs`
- ReDoc: `http://localhost:8060/redoc`

## Docker Deployment

### Auto-Restart Configuration

The container is configured with `restart: unless-stopped` policy, which means:
- ✅ Container automatically restarts if it crashes
- ✅ Container starts automatically when Docker daemon starts
- ✅ Container starts automatically after system reboot
- ❌ Container won't restart if explicitly stopped with `docker stop`

### Build and Run

```bash
# Build the image
cd docker && ./build.sh

# Setup environment (for docker-compose)
./setup-env.sh

# Run with Docker Compose (recommended)
docker-compose up -d

# Or run manually with auto-restart
./run.sh
```

### Manual Docker Run with Auto-Restart

```bash
docker run -d -p 8060:8060 \
  --restart unless-stopped \
  -v $(pwd)/config:/app/config:ro \
  -v $(pwd)/logs:/app/logs \
  -v $(pwd)/cache:/app/cache \
  -v /var/run/docker.sock:/var/run/docker.sock \
  --user $(id -u):$(id -g) \
  --network smart-assistant \
  mcp-dochub-server:latest
```

## Development

Clone the repository and install in development mode:

```bash
git clone https://github.com/yourusername/mcp-empty-server.git
cd mcp-empty-server
pip install -e ".[dev]"
```

Run tests:

```bash
pytest
```

Format code:

```bash
black .
```

## License

MIT License 