"""Blog resources providing context and data."""

from nextmcp import resource, resource_template


@resource(
    uri="blog://stats", description="Blog statistics and analytics", mime_type="application/json"
)
def blog_stats() -> dict:
    """Provide blog statistics."""
    return {
        "total_posts": 2,
        "total_views": 1500,
        "top_posts": [
            {"id": "1", "title": "Welcome to NextMCP", "views": 800},
            {"id": "2", "title": "Convention-based Structure", "views": 700},
        ],
        "popular_topics": ["MCP", "Python", "Development"],
    }


@resource(
    uri="blog://config",
    description="Blog configuration and guidelines",
    mime_type="application/json",
)
def blog_config() -> dict:
    """Provide blog configuration."""
    return {
        "blog_name": "NextMCP Blog",
        "guidelines": {
            "min_words": 300,
            "max_words": 2000,
            "required_sections": ["introduction", "main_content", "conclusion"],
            "tone": "professional yet approachable",
        },
        "seo": {
            "max_title_length": 60,
            "meta_description_length": 160,
        },
    }


@resource_template(
    uri_pattern="blog://posts/{post_id}",
    description="Individual blog post by ID",
)
def blog_post_resource(post_id: str) -> dict:
    """Get a specific blog post as a resource."""
    # Import here to avoid circular dependency
    from tools.posts import POSTS

    if post_id not in POSTS:
        raise ValueError(f"Post {post_id} not found")

    return POSTS[post_id]


@resource(
    uri="blog://authors",
    description="List of blog authors",
    mime_type="application/json",
)
def blog_authors() -> dict:
    """List blog authors."""
    return {
        "authors": [
            {"id": "admin", "name": "Admin User", "role": "Administrator", "posts": 2},
            {"id": "anonymous", "name": "Anonymous", "role": "Guest", "posts": 0},
        ]
    }
