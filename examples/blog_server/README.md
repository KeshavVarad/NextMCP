# Blog Server - Convention-based NextMCP Example

This example demonstrates NextMCP's convention-based project structure with automatic discovery of tools, prompts, and resources.

## Project Structure

```
blog_server/
├── nextmcp.config.yaml      # Configuration file
├── server.py                 # Entry point
│
├── tools/                    # Auto-discovered tools
│   ├── __init__.py
│   └── posts.py             # 5 blog management tools
│
├── prompts/                  # Auto-discovered prompts
│   ├── __init__.py
│   └── workflows.py         # 3 workflow prompts
│
└── resources/                # Auto-discovered resources
    ├── __init__.py
    └── blog_resources.py    # 4 blog resources
```

## Features

### Tools (5)
- `create_post` - Create a new blog post
- `get_post` - Get a post by ID
- `list_posts` - List all posts
- `update_post` - Update an existing post
- `delete_post` - Delete a post

### Prompts (3)
- `write_post_prompt` - Guide for writing a new post
- `edit_post_prompt` - Guide for editing an existing post
- `content_strategy_prompt` - Generate a content strategy

### Resources (4)
- `blog://stats` - Blog statistics and analytics
- `blog://config` - Blog configuration and guidelines
- `blog://posts/{post_id}` - Individual posts (template)
- `blog://authors` - List of blog authors

## Running the Example

### 1. Install NextMCP

```bash
pip install nextmcp[all]
```

### 2. Run the Server

```bash
cd examples/blog_server
python server.py
```

The server will automatically:
1. Load `nextmcp.config.yaml`
2. Discover all tools in `tools/`
3. Discover all prompts in `prompts/`
4. Discover all resources in `resources/`
5. Register everything with the MCP server
6. Start serving

## Key Takeaways

### Convention over Configuration
No manual registration needed! Just organize your code in the standard directories:
- `tools/` for tools
- `prompts/` for prompts
- `resources/` for resources

### Single Line Setup
```python
app = NextMCP.from_config()
```

That's it! Everything is auto-discovered and registered.

### Configuration File
The `nextmcp.config.yaml` file controls:
- Project metadata (name, version, description)
- Auto-discovery settings
- Server configuration
- Middleware
- Feature flags

### Scalable Structure
As your project grows, you can organize files in subdirectories:
```
tools/
  posts/
    create.py
    read.py
    update.py
    delete.py
  comments/
    manage.py
```

All files are discovered recursively!

## Comparison with Manual Approach

### Before (Manual Registration)
```python
from nextmcp import NextMCP

app = NextMCP("blog-server")

@app.tool()
def create_post(title: str, content: str):
    ...

@app.tool()
def get_post(post_id: str):
    ...

# ... repeat for 10+ tools, prompts, resources
```

### After (Convention-based)
```python
from nextmcp import NextMCP

app = NextMCP.from_config()
```

That's it! Much cleaner and more maintainable.
