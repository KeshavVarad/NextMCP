# Knowledge Base MCP Server

A comprehensive example demonstrating all three MCP primitives working together in a practical knowledge base application.

## Overview

This example implements a knowledge base server that showcases:

- **Tools** (Model-driven) - Actions to search and manage articles
- **Prompts** (User-driven) - Templates for research and documentation workflows
- **Resources** (App-driven) - Access to knowledge base data and statistics

## Features

### Tools 🔧

1. **search_knowledge(query)** - Search for articles matching a query
2. **add_article(...)** - Add new articles to the knowledge base
3. **list_categories()** - List all available categories

### Prompts 📝

1. **research_prompt(topic, depth)** - Generate research queries
   - Arguments: topic, depth (basic/detailed/comprehensive)
   - Auto-completion for topics

2. **summary_report_prompt(category)** - Create category summary reports
   - Arguments: category
   - Auto-completion for categories

3. **document_prompt(topic, format)** - Generate documentation templates
   - Arguments: topic, format (tutorial/reference/guide/overview)
   - Auto-completion for formats

### Resources 📚

1. **kb://stats** - Knowledge base statistics (JSON)
2. **kb://config** - Configuration (JSON, subscribable)
3. **kb://articles/{article_id}** - Get specific article (template)
4. **kb://category/{category}** - Get all articles in a category (template)

## Installation

```bash
# From the repository root
pip install -e .

# Or with dependencies
pip install -e ".[all]"
```

## Usage

### Running the Server

```bash
# From this directory
python app.py
```

Output:
```
🚀 Starting Knowledge Base MCP Server...
📚 Articles: 3
🏷️  Categories: 2

Server capabilities:
  • 3 Tools (search_knowledge, add_article, list_categories)
  • 3 Prompts (research, summary_report, document)
  • 4 Resources (stats, config, articles/{id}, category/{name})

⚡ Server ready!
```

### Example Interactions

#### Using Tools

```python
# Search for articles
search_knowledge("Python")
# Returns: {"query": "Python", "count": 1, "results": [...]}

# Add a new article
add_article(
    article_id="async-python",
    title="Async Python Guide",
    content="Guide to async/await in Python",
    category="programming",
    tags=["python", "async", "guide"]
)

# List all categories
list_categories()
# Returns: ["frameworks", "programming"]
```

#### Using Prompts

Prompts guide the AI to perform complex workflows:

```python
# Research a topic in depth
research_prompt("NextMCP", depth="comprehensive")
# Generates a prompt that instructs the AI to:
# 1. Search the knowledge base
# 2. List related categories
# 3. Provide comprehensive coverage

# Create a category summary
summary_report_prompt("frameworks")
# Generates a prompt to create a summary report
```

#### Using Resources

Resources provide read-only access to data:

```python
# Get statistics
# URI: kb://stats
# Returns: {"total_articles": 3, "total_searches": 0, ...}

# Get configuration (subscribable)
# URI: kb://config
# Returns: {"name": "Knowledge Base", "version": "1.0.0", ...}

# Get a specific article
# URI: kb://articles/python
# Returns: {"id": "python", "title": "Python Programming", ...}

# Get all articles in a category
# URI: kb://category/frameworks
# Returns: {"category": "frameworks", "count": 2, "articles": {...}}
```

## Code Structure

```python
from nextmcp import NextMCP, argument

app = NextMCP("knowledge-base")

# Tools - Actions the AI can perform
@app.tool()
def search_knowledge(query: str) -> dict:
    # Implementation...

# Prompts - Workflow templates
@app.prompt(tags=["research"])
@argument("topic", suggestions=[...])
def research_prompt(topic: str, depth: str) -> str:
    # Return prompt template...

# Resources - Data access
@app.resource("kb://stats")
def kb_statistics() -> dict:
    # Return data...

# Resource Templates - Dynamic resources
@app.resource_template("kb://articles/{article_id}")
async def get_article(article_id: str) -> dict:
    # Return article data...

# Argument/Parameter Completion
@app.prompt_completion("research_prompt", "topic")
def complete_topics(partial: str) -> list[str]:
    # Return suggestions...
```

## How It Works

### The Three Primitives Working Together

1. **AI uses Tools** to perform actions:
   - Search the knowledge base
   - Add new articles
   - List available categories

2. **User invokes Prompts** to guide complex workflows:
   - Research prompts guide the AI to search and synthesize information
   - Report prompts structure the output format
   - Documentation prompts provide templates for content creation

3. **Application exposes Resources** for context:
   - Statistics provide current system state
   - Configuration shows what's available
   - Article and category resources give direct data access

### Example Workflow

1. User invokes: `/research-prompt topic="NextMCP" depth="comprehensive"`
2. AI receives the generated prompt which instructs it to:
   - Use `search_knowledge("NextMCP")` tool
   - Check `kb://stats` resource for context
   - Use `list_categories()` to understand scope
3. AI synthesizes the information and provides a comprehensive response

## Extending This Example

### Add More Tools

```python
@app.tool()
def delete_article(article_id: str) -> dict:
    # Delete article implementation
```

### Add More Prompts

```python
@app.prompt()
@argument("old_id", suggestions=lambda: list(KNOWLEDGE_BASE.keys()))
@argument("new_id")
def rename_article_prompt(old_id: str, new_id: str) -> str:
    # Prompt for renaming articles
```

### Add More Resources

```python
@app.resource("kb://recent", mime_type="application/json")
def recent_articles() -> list:
    # Return recently added articles
```

### Enable Subscriptions

```python
# After updating configuration
app.notify_resource_changed("kb://config")
```

## Key Takeaways

1. **Tools** are active - the AI decides when to call them
2. **Prompts** are templates - users explicitly invoke them
3. **Resources** are passive - applications provide them as context
4. All three work together to create powerful, flexible interactions

## Learn More

- [NextMCP Documentation](../../README.md)
- [MCP Protocol Specification](https://modelcontextprotocol.io)
- [Other Examples](../)
