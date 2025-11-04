"""
Knowledge Base MCP Server - Demonstrates all three MCP primitives.

This example shows how Tools, Prompts, and Resources work together:
- Tools: Actions to search and manage the knowledge base
- Prompts: Templates for generating queries and reports
- Resources: Access to knowledge base data and statistics
"""

from datetime import datetime

from nextmcp import NextMCP, argument

# Initialize the app
app = NextMCP("knowledge-base", description="A knowledge base server with search and documentation")

# Sample in-memory knowledge base
KNOWLEDGE_BASE = {
    "python": {
        "title": "Python Programming",
        "content": "Python is a high-level, interpreted programming language.",
        "category": "programming",
        "tags": ["python", "programming", "language"],
        "created": "2025-01-01",
    },
    "fastmcp": {
        "title": "FastMCP Framework",
        "content": "FastMCP is a framework for building MCP servers.",
        "category": "frameworks",
        "tags": ["mcp", "framework", "server"],
        "created": "2025-01-02",
    },
    "nextmcp": {
        "title": "NextMCP SDK",
        "content": "NextMCP is a production-grade SDK for building MCP servers with minimal boilerplate.",
        "category": "frameworks",
        "tags": ["mcp", "sdk", "nextmcp"],
        "created": "2025-01-03",
    },
}

STATS = {
    "total_searches": 0,
    "total_articles": len(KNOWLEDGE_BASE),
    "last_updated": datetime.now().isoformat(),
}


# ============================================================================
# TOOLS - Model-driven actions
# ============================================================================


@app.tool()
def search_knowledge(query: str) -> dict:
    """
    Search the knowledge base for articles matching the query.

    Args:
        query: Search query string

    Returns:
        Dictionary with search results
    """
    STATS["total_searches"] += 1
    results = []

    query_lower = query.lower()
    for key, article in KNOWLEDGE_BASE.items():
        # Simple search: check if query appears in title, content, or tags
        if (
            query_lower in article["title"].lower()
            or query_lower in article["content"].lower()
            or any(query_lower in tag for tag in article["tags"])
        ):
            results.append({"id": key, **article})

    return {"query": query, "count": len(results), "results": results}


@app.tool()
def add_article(article_id: str, title: str, content: str, category: str, tags: list[str]) -> dict:
    """
    Add a new article to the knowledge base.

    Args:
        article_id: Unique identifier for the article
        title: Article title
        content: Article content
        category: Category (programming, frameworks, etc.)
        tags: List of tags

    Returns:
        Confirmation message
    """
    if article_id in KNOWLEDGE_BASE:
        return {"success": False, "error": f"Article '{article_id}' already exists"}

    KNOWLEDGE_BASE[article_id] = {
        "title": title,
        "content": content,
        "category": category,
        "tags": tags,
        "created": datetime.now().isoformat(),
    }

    STATS["total_articles"] = len(KNOWLEDGE_BASE)
    STATS["last_updated"] = datetime.now().isoformat()

    return {"success": True, "message": f"Article '{article_id}' added successfully"}


@app.tool()
def list_categories() -> list[str]:
    """
    List all unique categories in the knowledge base.

    Returns:
        List of category names
    """
    categories = {article["category"] for article in KNOWLEDGE_BASE.values()}
    return sorted(categories)


# ============================================================================
# PROMPTS - User-driven workflow templates
# ============================================================================


@app.prompt(description="Generate a research query", tags=["research", "search"])
@argument(
    "topic", description="Research topic", suggestions=["Python", "MCP", "FastMCP", "NextMCP"]
)
@argument("depth", description="Research depth", suggestions=["basic", "detailed", "comprehensive"])
def research_prompt(topic: str, depth: str = "basic") -> str:
    """Generate a prompt for researching a topic in the knowledge base."""
    depth_instructions = {
        "basic": "Provide a brief overview and key points.",
        "detailed": "Provide detailed information with examples and use cases.",
        "comprehensive": "Provide comprehensive coverage including history, examples, best practices, and related topics.",
    }

    return f"""Research the topic: {topic}

Depth level: {depth}
Instructions: {depth_instructions.get(depth, depth_instructions["basic"])}

Use the following tools to gather information:
1. search_knowledge("{topic}") - Search for articles about {topic}
2. list_categories() - See what categories are available

After gathering information, provide a summary based on the {depth} depth level.
"""


@app.prompt(description="Generate a summary report", tags=["reporting"])
@argument("category", description="Category to summarize")
def summary_report_prompt(category: str) -> str:
    """Generate a prompt for creating a category summary report."""
    return f"""Create a summary report for the '{category}' category.

Steps:
1. Use search_knowledge() to find all articles in the '{category}' category
2. List the key articles with their titles and main points
3. Identify common themes and important topics
4. Provide recommendations for areas that need more documentation

Use the resource://stats resource to check current knowledge base statistics.
"""


@app.prompt(description="Add new documentation", tags=["content", "documentation"])
@argument("topic", description="Topic to document")
@argument("format", suggestions=["tutorial", "reference", "guide", "overview"])
def document_prompt(topic: str, format: str = "guide") -> str:
    """Generate a prompt for creating new documentation."""
    return f"""Create new documentation for: {topic}
Format: {format}

Steps:
1. First, use search_knowledge("{topic}") to check if documentation already exists
2. If it exists, suggest improvements or related topics
3. If it doesn't exist, outline what should be included:
   - For tutorials: Step-by-step instructions with examples
   - For reference: Complete API/feature documentation
   - For guides: Best practices and use cases
   - For overview: High-level introduction and key concepts

4. Use add_article() to add the new documentation when ready
   - Choose an appropriate article_id (lowercase, hyphen-separated)
   - Select the right category
   - Add relevant tags for discoverability
"""


# Prompt argument completion
@app.prompt_completion("summary_report_prompt", "category")
def complete_categories(partial: str) -> list[str]:
    """Provide category suggestions for the summary report prompt."""
    categories = list_categories()
    return [cat for cat in categories if partial.lower() in cat.lower()]


# ============================================================================
# RESOURCES - Application-driven context providers
# ============================================================================


@app.resource("kb://stats", description="Knowledge base statistics", mime_type="application/json")
def kb_statistics() -> dict:
    """Provide current knowledge base statistics."""
    return {
        "total_articles": STATS["total_articles"],
        "total_searches": STATS["total_searches"],
        "last_updated": STATS["last_updated"],
        "categories": list_categories(),
    }


@app.resource(
    "kb://config",
    description="Knowledge base configuration",
    mime_type="application/json",
    subscribable=True,
)
async def kb_config() -> dict:
    """Provide knowledge base configuration (subscribable for changes)."""
    return {
        "name": "Knowledge Base",
        "version": "1.0.0",
        "max_results": 100,
        "search_enabled": True,
        "categories_enabled": list_categories(),
    }


# Resource templates for dynamic access
@app.resource_template("kb://articles/{article_id}", description="Get a specific article by ID")
async def get_article(article_id: str) -> dict:
    """Retrieve a specific article from the knowledge base."""
    if article_id not in KNOWLEDGE_BASE:
        return {"error": f"Article '{article_id}' not found"}

    return {"id": article_id, **KNOWLEDGE_BASE[article_id]}


@app.resource_template("kb://category/{category}", description="Get all articles in a category")
def get_category_articles(category: str) -> dict:
    """Retrieve all articles in a specific category."""
    articles = {
        key: article for key, article in KNOWLEDGE_BASE.items() if article["category"] == category
    }

    return {"category": category, "count": len(articles), "articles": articles}


# Template parameter completion
@app.template_completion("get_article", "article_id")
def complete_article_ids(partial: str) -> list[str]:
    """Suggest article IDs."""
    return [aid for aid in KNOWLEDGE_BASE.keys() if partial in aid]


@app.template_completion("get_category_articles", "category")
def complete_category_names(partial: str) -> list[str]:
    """Suggest category names."""
    return complete_categories(partial)


# ============================================================================
# Main entry point
# ============================================================================

if __name__ == "__main__":
    print("🚀 Starting Knowledge Base MCP Server...")
    print(f"📚 Articles: {len(KNOWLEDGE_BASE)}")
    print(f"🏷️  Categories: {len(list_categories())}")
    print("\nServer capabilities:")
    print("  • 3 Tools (search_knowledge, add_article, list_categories)")
    print("  • 3 Prompts (research, summary_report, document)")
    print("  • 4 Resources (stats, config, articles/{id}, category/{name})")
    print("\n⚡ Server ready!\n")

    app.run()
