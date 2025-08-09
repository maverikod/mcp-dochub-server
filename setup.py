"""Setup script for MCP Empty Server."""

from setuptools import setup, find_packages

# Read the contents of README file
from pathlib import Path
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text()

# Read version
exec(open('mcp_empty_server/version.py').read())

setup(
    name="mcp-empty-server",
    version=__version__,
    author="Your Name",
    author_email="your.email@example.com",
    description="Empty server with command autodiscovery support using mcp_proxy_adapter",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/mcp-empty-server",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Internet :: WWW/HTTP :: HTTP Servers",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: System :: Networking",
    ],
    python_requires=">=3.8",
    install_requires=[
        "mcp-proxy-adapter>=1.0.0",
        "uvicorn>=0.20.0",
        "fastapi>=0.95.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-asyncio>=0.21.0",
            "black>=23.0.0",
            "flake8>=6.0.0",
            "mypy>=1.0.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "mcp-empty-server=mcp_empty_server.server:main",
        ],
    },
    include_package_data=True,
    zip_safe=False,
) 