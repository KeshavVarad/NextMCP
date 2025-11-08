"""
Example: A secure MCP server with proper input validation.

This server demonstrates security best practices:
- Strict input validation with patterns and length limits
- Enum-based restrictions for limited options
- Clear authentication indicators
- No dangerous operations without safeguards
"""

from nextmcp import NextMCP

app = NextMCP("secure-file-server", "Secure file management server with authentication")


@app.tool(description="List files in allowed directories (requires authentication)")
def list_files(directory: str) -> dict:
    """
    List files in a directory.

    Only allows accessing pre-approved directories.
    """
    # In real implementation, would check authentication here
    allowed_dirs = ["documents", "images", "downloads"]

    if directory not in allowed_dirs:
        return {"error": "Directory not allowed"}

    return {
        "directory": directory,
        "files": ["file1.txt", "file2.txt"],  # Mock data
    }


@app.tool(description="Read file content (requires authentication, audit logged)")
def read_file(filename: str) -> dict:
    """
    Read a file by name.

    Only accepts alphanumeric filenames with common extensions.
    """
    import re

    # Validate filename format
    if not re.match(r"^[a-zA-Z0-9_-]+\.[a-z]{2,4}$", filename):
        return {"error": "Invalid filename format"}

    if len(filename) > 255:
        return {"error": "Filename too long"}

    return {"filename": filename, "content": "File content here"}


@app.tool(description="Search files by keyword (requires authentication, rate limited)")
def search_files(query: str, directory: str = "documents") -> dict:
    """
    Search for files containing a keyword.

    Strict validation to prevent injection attacks.
    """
    allowed_dirs = ["documents", "images", "downloads"]

    if directory not in allowed_dirs:
        return {"error": "Invalid directory"}

    # Validate query is safe
    if len(query) > 100:
        return {"error": "Query too long"}

    # Only allow alphanumeric and spaces
    import re

    if not re.match(r"^[a-zA-Z0-9 ]+$", query):
        return {"error": "Invalid query format"}

    return {"query": query, "results": ["result1.txt", "result2.txt"]}


if __name__ == "__main__":
    # Generate manifest
    print("Generating manifest for secure server...")
    manifest = app.generate_manifest("manifest.json")

    print("\n✅ Manifest generated!")
    print(f"  Tools: {len(manifest['tools'])}")

    # Validate it
    from nextmcp.security import validate_manifest

    print("\nValidating manifest...")
    result, assessment = validate_manifest(manifest)

    print(
        f"\n{'✅' if result.valid else '❌'} Validation: {'PASSED' if result.valid else 'FAILED'}"
    )
    print(f"Risk Level: {assessment.overall_risk.value.upper()}")
    print(f"Risk Score: {assessment.risk_score}/100")

    print(f"\nIssues found: {len(assessment.issues)}")
    for issue in assessment.issues:
        print(f"  [{issue.level.value.upper()}] {issue.title}")

    print("\n" + "=" * 60)
    print("This server should have LOW to MEDIUM risk because:")
    print("- All inputs are strictly validated")
    print("- File paths use enums or strict patterns")
    print("- Queries have length limits and character whitelists")
    print("- Authentication is mentioned in descriptions")
    print("=" * 60)
