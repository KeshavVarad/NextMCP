"""Workflow prompts for blog operations."""

from nextmcp import argument, prompt


@prompt(description="Create and publish a new blog post", tags=["blog", "writing"])
@argument("topic", description="The topic to write about", type="string")
@argument("tone", description="Writing tone", suggestions=["formal", "casual", "technical"])
def write_post_prompt(topic: str, tone: str = "casual") -> str:
    """Generate a prompt for writing a blog post."""
    return f"""
Write a blog post about: {topic}

Tone: {tone}

Use the following tools:
- create_post: To save the final post
- list_posts: To check existing posts and avoid duplication

Check these resources:
- resource://blog/stats - To understand audience preferences
- resource://blog/config - To follow blog guidelines
"""


@prompt(description="Edit and improve an existing post", tags=["blog", "editing"])
@argument("post_id", description="ID of the post to edit", type="string")
def edit_post_prompt(post_id: str) -> str:
    """Generate a prompt for editing a blog post."""
    return f"""
Edit and improve blog post ID: {post_id}

Steps:
1. Use get_post tool to retrieve the current post
2. Review the content for:
   - Grammar and spelling
   - Clarity and flow
   - SEO optimization
3. Use update_post tool to save improvements

Check resource://blog/posts/{post_id} for the current version
"""


@prompt(description="Generate a content strategy", tags=["blog", "planning"])
def content_strategy_prompt() -> str:
    """Generate a content planning prompt."""
    return """
Create a content strategy for the blog.

Use these tools:
- list_posts: Review existing content
- create_post: Add new strategic posts

Review these resources:
- resource://blog/stats - Analyze what's performing well
- resource://blog/posts/* - Review all existing posts
"""
