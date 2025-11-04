#!/usr/bin/env python3
"""
Blog Server - Convention-based NextMCP Example

This example demonstrates the convention-based project structure with auto-discovery.
Simply run this file to start the server with all tools, prompts, and resources
automatically discovered and registered.

Usage:
    python server.py
"""

from nextmcp import NextMCP

# Load from config file and auto-discover all primitives
app = NextMCP.from_config()

if __name__ == "__main__":
    # The app is already configured with:
    # - 5 tools from tools/posts.py
    # - 3 prompts from prompts/workflows.py
    # - 4 resources from resources/blog_resources.py
    print(f"Starting {app.name}...")
    print(f"Auto-discovered {len(app.get_tools())} tools")
    print(f"Auto-discovered {len(app.get_prompts())} prompts")
    print(f"Auto-discovered {len(app.get_resources())} resources")
    app.run()
