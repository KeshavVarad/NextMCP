"""
Setup script for NextMCP

This setup.py is maintained for backward compatibility and editable installs.
The primary build configuration is in pyproject.toml.
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read the README file
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text(encoding="utf-8")

setup(
    name="nextmcp",
    version="0.1.0",
    author="NextMCP Contributors",
    description="Production-grade MCP server toolkit with minimal boilerplate",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/KeshavVarad/NextMCP",
    packages=find_packages(exclude=["tests", "tests.*", "examples", "examples.*"]),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Internet :: WWW/HTTP :: HTTP Servers",
    ],
    python_requires=">=3.8",
    install_requires=[
        "fastmcp>=0.1.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
            "black>=23.0.0",
            "ruff>=0.1.0",
            "mypy>=1.0.0",
        ],
        "cli": [
            "typer>=0.9.0",
            "rich>=13.0.0",
        ],
        "config": [
            "python-dotenv>=1.0.0",
            "pyyaml>=6.0.0",
        ],
        "schema": [
            "pydantic>=2.0.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "mcp=nextmcp.cli:main",
        ],
    },
    include_package_data=True,
    zip_safe=False,
)
