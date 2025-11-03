# Plugin Example

This example demonstrates the NextMCP plugin system, showing how to create, discover, and use plugins.

## Features

- **Plugin Discovery**: Automatically discover plugins from a directory
- **Multiple Plugin Types**: Tools, middleware, and combined plugins
- **Plugin Lifecycle**: Initialize, load, and unload plugins
- **Plugin Metadata**: Version, description, author, and dependencies

## Included Plugins

### 1. Math Plugin (`math_plugin.py`)
Adds mathematical operation tools:
- `add(a, b)` - Add two numbers
- `multiply(a, b)` - Multiply two numbers
- `power(base, exponent)` - Calculate power

### 2. Timing Plugin (`timing_plugin.py`)
Adds middleware that measures tool execution time:
- Tracks how long each tool takes to execute
- Prints timing information for debugging

### 3. String Plugin (`string_plugin.py`)
Adds string manipulation tools:
- `uppercase(text)` - Convert to uppercase
- `lowercase(text)` - Convert to lowercase
- `reverse(text)` - Reverse a string
- `count_words(text)` - Count words

## Running the Example

```bash
cd examples/plugin_example
python app.py
```

You should see:
1. Plugins being discovered and loaded
2. List of loaded plugins with metadata
3. All registered tools from plugins
4. Tool execution tests with timing information

## Creating Your Own Plugin

### Basic Plugin Structure

```python
from nextmcp import Plugin

class MyPlugin(Plugin):
    name = "my-plugin"
    version = "1.0.0"
    description = "My custom plugin"
    author = "Your Name"

    def on_load(self, app):
        # Register tools
        @app.tool()
        def my_tool(param: str) -> str:
            return f"Hello {param}"
```

### Plugin with Middleware

```python
class MyMiddlewarePlugin(Plugin):
    name = "my-middleware"
    version = "1.0.0"

    def on_load(self, app):
        def my_middleware(fn):
            def wrapper(*args, **kwargs):
                # Before tool execution
                result = fn(*args, **kwargs)
                # After tool execution
                return result
            return wrapper

        app.add_middleware(my_middleware)
```

### Plugin with Dependencies

```python
class DependentPlugin(Plugin):
    name = "dependent"
    version = "1.0.0"
    dependencies = ["math-plugin"]  # Will load math-plugin first

    def on_load(self, app):
        # Your plugin code here
        pass
```

## Plugin Lifecycle Hooks

Plugins have three lifecycle hooks:

1. **`on_init()`** - Called during initialization, before app access
2. **`on_load(app)`** - Called when plugin is loaded, receives app instance
3. **`on_unload()`** - Called when plugin is unloaded, for cleanup

## Using Plugins in Your App

### Method 1: Auto-discovery

```python
from nextmcp import NextMCP

app = NextMCP("my-app")
app.discover_plugins("./plugins")
app.load_plugins()
```

### Method 2: Manual Loading

```python
from nextmcp import NextMCP
from my_plugins import MyPlugin

app = NextMCP("my-app")
app.use_plugin(MyPlugin)
```

### Method 3: Direct Plugin Manager

```python
app = NextMCP("my-app")
app.plugins.register_plugin_class(MyPlugin)
app.plugins.load_plugin("my-plugin")
```

## Plugin Best Practices

1. **Use clear names**: Choose descriptive, unique plugin names
2. **Version properly**: Use semantic versioning (major.minor.patch)
3. **Document well**: Add descriptions and docstrings
4. **Handle errors**: Catch exceptions in lifecycle hooks
5. **Declare dependencies**: List required plugins in dependencies
6. **Clean up**: Implement `on_unload()` for cleanup
7. **Test thoroughly**: Write tests for your plugins

## Plugin Directory Structure

```
my_app/
├── app.py
└── plugins/
    ├── plugin1.py
    ├── plugin2.py
    └── plugin3.py
```

Each plugin file can contain one or more Plugin classes. The plugin system will automatically discover and register all Plugin subclasses.

## Advanced Usage

### Accessing Plugin State

```python
# Get a specific plugin
plugin = app.plugins.get_plugin("my-plugin")
if plugin and plugin.is_loaded:
    # Access plugin properties
    print(plugin.version)
```

### Listing Plugins

```python
# Get information about all plugins
for info in app.plugins.list_plugins():
    print(f"{info['name']} v{info['version']} - {info['loaded']}")
```

### Unloading Plugins

```python
# Unload a specific plugin
app.plugins.unload_plugin("my-plugin")

# Unload all plugins
app.plugins.unload_all()
```

## Next Steps

- Create your own custom plugins
- Combine multiple plugins for complex functionality
- Share your plugins with the community
- Add plugin configuration support
- Implement plugin hot-reloading
