"""
Example: An INSECURE MCP server with multiple security vulnerabilities.

⚠️ WARNING: This is an example of what NOT to do!
This server demonstrates common security mistakes.

DO NOT use this in production!
"""

from nextmcp import NextMCP

app = NextMCP("insecure-server", "Example of insecure server - DO NOT USE")


@app.tool(description="Execute a SQL query")
def execute_query(query: str) -> dict:
    """
    Execute a SQL query.

    🚨 SECURITY ISSUE: SQL Injection!
    Accepting raw SQL from users is extremely dangerous.
    """
    # In real implementation, this would execute the query
    # Attacker could input: "DROP TABLE users; --"
    return {"query": query, "result": "Query executed"}


@app.tool(description="Read any file from the system")
def read_file(file_path: str) -> dict:
    """
    Read a file by path.

    🚨 SECURITY ISSUE: Path Traversal!
    No validation means attacker can read:
    - ../../../etc/passwd
    - C:\\Windows\\System32\\config\\SAM
    """
    return {"path": file_path, "content": "File content"}


@app.tool(description="Execute system command")
def run_command(command: str) -> dict:
    """
    Execute a system command.

    🚨 SECURITY ISSUE: Command Injection!
    Attacker could run ANY command on the server.
    """
    return {"command": command, "output": "Command output"}


@app.tool(description="Fetch data from a URL")
def fetch_url(url: str) -> dict:
    """
    Fetch data from any URL.

    🚨 SECURITY ISSUE: SSRF (Server-Side Request Forgery)!
    Attacker could:
    - Access internal network resources
    - Scan internal ports
    - Access cloud metadata APIs (AWS, GCP, Azure)
    """
    return {"url": url, "data": "Response data"}


@app.tool(description="Delete user account")
def delete_user(user_id: str, password: str) -> dict:
    """
    Delete a user account.

    🚨 SECURITY ISSUES:
    - No authentication mentioned (who can delete?)
    - Password in manifest (sensitive data)
    - Dangerous operation without safeguards
    """
    return {"user_id": user_id, "deleted": True}


@app.tool(description="Process data")
def process_data(data: dict) -> dict:
    """
    Process arbitrary data.

    🚨 SECURITY ISSUE: Unconstrained object!
    Accepts any JSON structure without validation.
    """
    return {"processed": True}


if __name__ == "__main__":
    # Generate manifest
    print("Generating manifest for INSECURE server...")
    print("⚠️  This server demonstrates what NOT to do!\n")

    manifest = app.generate_manifest("insecure_manifest.json")

    print("✅ Manifest generated!")
    print(f"  Tools: {len(manifest['tools'])}")

    # Validate it
    from nextmcp.security import validate_manifest

    print("\nValidating manifest...")
    result, assessment = validate_manifest(manifest)

    print(f"\n{'✅' if result.valid else '❌'} Structure: {'Valid' if result.valid else 'Invalid'}")
    print(f"Risk Level: {assessment.overall_risk.value.upper()}")
    print(f"Risk Score: {assessment.risk_score}/100")

    print(f"\n🚨 Issues found: {len(assessment.issues)}")

    # Group by severity
    critical = [i for i in assessment.issues if i.level.value == "critical"]
    high = [i for i in assessment.issues if i.level.value == "high"]
    medium = [i for i in assessment.issues if i.level.value == "medium"]

    if critical:
        print(f"\n🔴 CRITICAL Issues ({len(critical)}):")
        for issue in critical:
            print(f"  - {issue.title}")
            print(f"    {issue.description}")
            print(f"    💡 {issue.recommendation}\n")

    if high:
        print(f"🟠 HIGH Issues ({len(high)}):")
        for issue in high:
            print(f"  - {issue.title}")

    if medium:
        print(f"\n🟡 MEDIUM Issues ({len(medium)}):")
        for issue in medium:
            print(f"  - {issue.title}")

    print("\n" + "=" * 60)
    print("This server has CRITICAL security issues:")
    print("✗ SQL injection vulnerability")
    print("✗ Path traversal vulnerability")
    print("✗ Command injection vulnerability")
    print("✗ SSRF vulnerability")
    print("✗ Dangerous operations without authentication")
    print("✗ No input validation")
    print("\n❌ DO NOT deploy servers like this!")
    print("=" * 60)
