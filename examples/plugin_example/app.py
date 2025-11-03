"""
Plugin Example - Demonstrates NextMCP plugin system.

This example shows:
- Loading plugins from a directory
- Using individual plugins
- Combining multiple plugins
- Plugin lifecycle management
"""

from nextmcp import NextMCP, setup_logging

# Setup logging
setup_logging(level="INFO")

# Create the application
app = NextMCP(
    name="plugin-demo",
    description="Demonstration of NextMCP plugin system"
)

print("=" * 60)
print("NextMCP Plugin System Demo")
print("=" * 60)
print()

# Method 1: Discover and load plugins from directory
print("Method 1: Auto-discovery from directory")
print("-" * 60)
app.discover_plugins("./plugins")
app.load_plugins()
print()

# Method 2: Manually use a specific plugin
print("Method 2: Manual plugin loading")
print("-" * 60)
# from plugins.math_plugin import MathPlugin
# app.use_plugin(MathPlugin)
print("(Skipped - already loaded via discovery)")
print()

# Show loaded plugins
print("Loaded Plugins:")
print("-" * 60)
for plugin_info in app.plugins.list_plugins():
    status = "✓" if plugin_info["loaded"] else "✗"
    print(f"{status} {plugin_info['name']} v{plugin_info['version']}")
    print(f"  {plugin_info['description']}")
print()

# Show registered tools
print("Registered Tools:")
print("-" * 60)
tools = app.get_tools()
for tool_name in sorted(tools.keys()):
    tool = tools[tool_name]
    desc = getattr(tool, '_tool_description', 'No description')
    if desc:
        desc = desc.split('\n')[0]  # First line only
    print(f"  • {tool_name}: {desc}")
print()

# Test the tools
print("Testing Tools:")
print("=" * 60)

# Math plugin tools
print("\n1. Math Plugin Tools:")
print("-" * 60)
add_result = tools['add'](5, 3)
print(f"add(5, 3) = {add_result}")

multiply_result = tools['multiply'](4, 7)
print(f"multiply(4, 7) = {multiply_result}")

power_result = tools['power'](2, 8)
print(f"power(2, 8) = {power_result}")

# String plugin tools
print("\n2. String Plugin Tools:")
print("-" * 60)
text = "Hello NextMCP"
print(f"Original: {text}")
print(f"uppercase: {tools['uppercase'](text)}")
print(f"lowercase: {tools['lowercase'](text)}")
print(f"reverse: {tools['reverse'](text)}")
print(f"count_words: {tools['count_words'](text)}")

print("\n" + "=" * 60)
print("Demo Complete!")
print("=" * 60)
print()
print("The timing middleware from TimingPlugin is measuring all tool calls.")
print("Notice the timing information printed for each tool invocation.")
print()
print("To run the MCP server, uncomment the app.run() line below.")
print()

# Uncomment to run as MCP server
# if __name__ == "__main__":
#     app.run()
