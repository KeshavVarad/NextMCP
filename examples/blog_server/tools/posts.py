"""Tools for managing blog posts."""

from nextmcp import tool

# In-memory storage for demo
POSTS = {
    "1": {"id": "1", "title": "Welcome to NextMCP", "content": "This is the first post", "author": "admin"},
    "2": {"id": "2", "title": "Convention-based Structure", "content": "Auto-discovery is awesome!", "author": "admin"},
}


@tool()
def create_post(title: str, content: str, author: str = "anonymous") -> dict:
    """Create a new blog post."""
    post_id = str(len(POSTS) + 1)
    post = {
        "id": post_id,
        "title": title,
        "content": content,
        "author": author,
    }
    POSTS[post_id] = post
    return post


@tool()
def get_post(post_id: str) -> dict:
    """Get a blog post by ID."""
    if post_id not in POSTS:
        raise ValueError(f"Post {post_id} not found")
    return POSTS[post_id]


@tool()
def list_posts() -> list[dict]:
    """List all blog posts."""
    return list(POSTS.values())


@tool()
def update_post(post_id: str, title: str | None = None, content: str | None = None) -> dict:
    """Update an existing blog post."""
    if post_id not in POSTS:
        raise ValueError(f"Post {post_id} not found")

    if title:
        POSTS[post_id]["title"] = title
    if content:
        POSTS[post_id]["content"] = content

    return POSTS[post_id]


@tool()
def delete_post(post_id: str) -> dict:
    """Delete a blog post."""
    if post_id not in POSTS:
        raise ValueError(f"Post {post_id} not found")

    deleted = POSTS.pop(post_id)
    return {"deleted": True, "post": deleted}
