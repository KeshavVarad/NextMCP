"""
Manifest security validation and risk assessment.

This module validates MCP server manifests for security issues and assigns
risk scores. It focuses on catching obvious security problems but should be
used as part of a comprehensive security strategy.

⚠️ LIMITATIONS:
- Cannot detect malicious code in server implementation
- Cannot verify authentication/authorization is properly implemented
- Cannot detect business logic vulnerabilities
- Cannot prevent supply chain attacks
- Validation can be bypassed by sophisticated attackers

Always combine with: code review, penetration testing, and runtime monitoring.
"""

import json
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class RiskLevel(Enum):
    """Risk level classification."""

    CRITICAL = "critical"  # Immediate security concern, block deployment
    HIGH = "high"  # Serious issue, requires review
    MEDIUM = "medium"  # Potential issue, should be reviewed
    LOW = "low"  # Minor issue or best practice violation
    INFO = "info"  # Informational, no action required


@dataclass
class SecurityIssue:
    """A security issue found during validation."""

    level: RiskLevel
    category: str  # e.g., "input_validation", "dangerous_operation", "schema_issue"
    title: str
    description: str
    location: str  # Where in the manifest (e.g., "tools[0].inputSchema")
    recommendation: str
    cwe_id: str | None = None  # Common Weakness Enumeration ID if applicable

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "level": self.level.value,
            "category": self.category,
            "title": self.title,
            "description": self.description,
            "location": self.location,
            "recommendation": self.recommendation,
            "cwe_id": self.cwe_id,
        }


@dataclass
class RiskAssessment:
    """Overall risk assessment for a manifest."""

    overall_risk: RiskLevel
    risk_score: int  # 0-100, higher = more risky
    issues: list[SecurityIssue] = field(default_factory=list)
    summary: dict[str, int] = field(default_factory=dict)  # Count by level

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "overall_risk": self.overall_risk.value,
            "risk_score": self.risk_score,
            "summary": self.summary,
            "issues": [issue.to_dict() for issue in self.issues],
        }


@dataclass
class ValidationResult:
    """Result of manifest validation."""

    valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    manifest: dict | None = None

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "valid": self.valid,
            "errors": self.errors,
            "warnings": self.warnings,
        }


class ManifestValidator:
    """
    Validates MCP server manifests for security issues.

    This validator performs static analysis of manifest.json files to identify
    potential security risks. It checks for:
    - Dangerous operation patterns
    - Missing input validation
    - Overly permissive schemas
    - Sensitive data exposure
    - Structural issues

    ⚠️ IMPORTANT LIMITATIONS:
    - Only validates the manifest, not the actual server code
    - Cannot detect if server implementation matches manifest
    - Cannot detect runtime vulnerabilities
    - Cannot verify authentication/authorization
    - Can be fooled by sophisticated attackers

    Use this as an initial screening tool, not a complete security solution.

    Example:
        validator = ManifestValidator()

        # Validate a manifest file
        result = validator.validate_file("manifest.json")
        if not result.valid:
            print("Validation failed:", result.errors)

        # Assess risk
        assessment = validator.assess_risk(manifest)
        print(f"Risk level: {assessment.overall_risk}")
        for issue in assessment.issues:
            print(f"- {issue.title}")
    """

    # Dangerous keywords in tool names (potential security risks)
    DANGEROUS_KEYWORDS = [
        "delete",
        "remove",
        "drop",
        "destroy",
        "execute",
        "exec",
        "eval",
        "run",
        "system",
        "shell",
        "cmd",
        "command",
        "admin",
        "root",
        "sudo",
        "kill",
        "terminate",
        "modify",
        "update",
        "write",
        "create",
        "install",
        "uninstall",
    ]

    # Sensitive data keywords
    SENSITIVE_KEYWORDS = [
        "password",
        "passwd",
        "secret",
        "api_key",
        "apikey",
        "token",
        "credential",
        "private_key",
        "privatekey",
        "auth",
        "ssn",
        "social_security",
        "credit_card",
        "cvv",
    ]

    # High-risk parameter names
    RISKY_PARAMS = [
        "path",
        "file",
        "filename",
        "directory",
        "dir",
        "url",
        "uri",
        "command",
        "cmd",
        "query",
        "sql",
        "code",
        "script",
    ]

    def __init__(self):
        """Initialize the validator."""
        self.issues: list[SecurityIssue] = []

    def validate_file(self, manifest_path: str | Path) -> ValidationResult:
        """
        Validate a manifest file.

        Args:
            manifest_path: Path to manifest.json file

        Returns:
            ValidationResult with validation status and any errors
        """
        manifest_path = Path(manifest_path)

        if not manifest_path.exists():
            return ValidationResult(
                valid=False, errors=[f"Manifest file not found: {manifest_path}"]
            )

        try:
            with open(manifest_path) as f:
                manifest = json.load(f)
        except json.JSONDecodeError as e:
            return ValidationResult(valid=False, errors=[f"Invalid JSON: {e}"])
        except Exception as e:
            return ValidationResult(valid=False, errors=[f"Error reading file: {e}"])

        return self.validate(manifest)

    def validate(self, manifest: dict) -> ValidationResult:
        """
        Validate a manifest dictionary.

        Args:
            manifest: Manifest data as dictionary

        Returns:
            ValidationResult with validation status
        """
        errors = []
        warnings = []

        # Check required fields
        if "implementation" not in manifest:
            errors.append("Missing required field: implementation")
        else:
            impl = manifest["implementation"]
            if "name" not in impl:
                errors.append("Missing required field: implementation.name")
            if "version" not in impl:
                errors.append("Missing required field: implementation.version")

        # Check MCP version
        if "mcpVersion" not in manifest:
            warnings.append("Missing mcpVersion field")

        # Validate tools
        tools = manifest.get("tools", [])
        if not isinstance(tools, list):
            errors.append("Field 'tools' must be an array")
        else:
            for i, tool in enumerate(tools):
                tool_errors = self._validate_tool(tool, f"tools[{i}]")
                errors.extend(tool_errors)

        # Validate prompts
        prompts = manifest.get("prompts", [])
        if not isinstance(prompts, list):
            errors.append("Field 'prompts' must be an array")
        else:
            for i, prompt in enumerate(prompts):
                prompt_errors = self._validate_prompt(prompt, f"prompts[{i}]")
                errors.extend(prompt_errors)

        # Validate resources
        resources = manifest.get("resources", [])
        if not isinstance(resources, list):
            errors.append("Field 'resources' must be an array")
        else:
            for i, resource in enumerate(resources):
                resource_errors = self._validate_resource(resource, f"resources[{i}]")
                errors.extend(resource_errors)

        return ValidationResult(
            valid=len(errors) == 0, errors=errors, warnings=warnings, manifest=manifest
        )

    def _validate_tool(self, tool: dict, location: str) -> list[str]:
        """Validate a tool definition."""
        errors = []

        if "name" not in tool:
            errors.append(f"{location}: Missing required field 'name'")
        if "description" not in tool:
            errors.append(f"{location}: Missing required field 'description'")
        if "inputSchema" not in tool:
            errors.append(f"{location}: Missing required field 'inputSchema'")

        return errors

    def _validate_prompt(self, prompt: dict, location: str) -> list[str]:
        """Validate a prompt definition."""
        errors = []

        if "name" not in prompt:
            errors.append(f"{location}: Missing required field 'name'")

        return errors

    def _validate_resource(self, resource: dict, location: str) -> list[str]:
        """Validate a resource definition."""
        errors = []

        if "uri" not in resource:
            errors.append(f"{location}: Missing required field 'uri'")
        if "name" not in resource:
            errors.append(f"{location}: Missing required field 'name'")

        return errors

    def assess_risk(self, manifest: dict | str | Path) -> RiskAssessment:
        """
        Assess security risk of a manifest.

        Args:
            manifest: Manifest dictionary, JSON string, or file path

        Returns:
            RiskAssessment with risk level and identified issues
        """
        # Load manifest if needed
        if isinstance(manifest, (str, Path)):
            manifest_path = Path(manifest)
            if manifest_path.exists():
                with open(manifest_path) as f:
                    manifest = json.load(f)
            else:
                manifest = json.loads(manifest)

        self.issues = []

        # Perform all security checks
        self._check_dangerous_tools(manifest)
        self._check_input_validation(manifest)
        self._check_sensitive_data(manifest)
        self._check_risky_parameters(manifest)
        self._check_capabilities(manifest)
        self._check_authentication_indicators(manifest)

        # Calculate risk score and overall level
        risk_score = self._calculate_risk_score()
        overall_risk = self._determine_overall_risk(risk_score)

        # Count issues by level
        summary = {
            "critical": sum(1 for i in self.issues if i.level == RiskLevel.CRITICAL),
            "high": sum(1 for i in self.issues if i.level == RiskLevel.HIGH),
            "medium": sum(1 for i in self.issues if i.level == RiskLevel.MEDIUM),
            "low": sum(1 for i in self.issues if i.level == RiskLevel.LOW),
            "info": sum(1 for i in self.issues if i.level == RiskLevel.INFO),
        }

        return RiskAssessment(
            overall_risk=overall_risk,
            risk_score=risk_score,
            issues=self.issues.copy(),
            summary=summary,
        )

    def _check_dangerous_tools(self, manifest: dict):
        """Check for tools with dangerous names."""
        tools = manifest.get("tools", [])

        for i, tool in enumerate(tools):
            name = tool.get("name", "").lower()
            desc = tool.get("description", "").lower()

            for keyword in self.DANGEROUS_KEYWORDS:
                if keyword in name or keyword in desc:
                    self.issues.append(
                        SecurityIssue(
                            level=RiskLevel.HIGH,
                            category="dangerous_operation",
                            title=f"Potentially dangerous tool: {tool.get('name')}",
                            description=f"Tool name/description contains keyword '{keyword}' which suggests a potentially destructive or privileged operation",
                            location=f"tools[{i}]",
                            recommendation="Carefully review this tool's implementation for: proper authorization, input validation, audit logging, and rate limiting. Consider if this operation should be exposed via MCP.",
                            cwe_id="CWE-749",  # Exposed Dangerous Method or Function
                        )
                    )
                    break  # Only report once per tool

    def _check_input_validation(self, manifest: dict):
        """Check for missing or weak input validation."""
        tools = manifest.get("tools", [])

        for i, tool in enumerate(tools):
            schema = tool.get("inputSchema", {})
            properties = schema.get("properties", {})

            for param_name, param_spec in properties.items():
                param_type = param_spec.get("type")
                location = f"tools[{i}].inputSchema.properties.{param_name}"

                # Check for unbounded strings
                if param_type == "string":
                    # Skip if enum is present - enum provides bounds
                    if "maxLength" not in param_spec and "enum" not in param_spec:
                        self.issues.append(
                            SecurityIssue(
                                level=RiskLevel.MEDIUM,
                                category="input_validation",
                                title=f"Unbounded string parameter: {param_name}",
                                description=f"Parameter '{param_name}' in tool '{tool.get('name')}' has no maxLength constraint, making it vulnerable to buffer overflow or DoS attacks",
                                location=location,
                                recommendation="Add 'maxLength' constraint to the schema. Example: \"maxLength\": 1000",
                                cwe_id="CWE-20",  # Improper Input Validation
                            )
                        )

                    if "pattern" not in param_spec and "enum" not in param_spec:
                        # Only warn if it's a risky parameter type
                        if any(risk in param_name.lower() for risk in self.RISKY_PARAMS):
                            self.issues.append(
                                SecurityIssue(
                                    level=RiskLevel.HIGH,
                                    category="input_validation",
                                    title=f"Unvalidated risky parameter: {param_name}",
                                    description=f"Parameter '{param_name}' accepts any string without format validation. This is dangerous for file paths, URLs, or commands.",
                                    location=location,
                                    recommendation="Add 'pattern' constraint to whitelist valid formats, or use 'enum' to restrict to specific values.",
                                    cwe_id="CWE-20",
                                )
                            )

                # Check for unconstrained objects
                if param_type == "object" and "properties" not in param_spec:
                    self.issues.append(
                        SecurityIssue(
                            level=RiskLevel.MEDIUM,
                            category="input_validation",
                            title=f"Unconstrained object parameter: {param_name}",
                            description=f"Parameter '{param_name}' accepts any object structure without validation",
                            location=location,
                            recommendation="Define 'properties' to specify allowed object structure, or use 'additionalProperties: false'",
                            cwe_id="CWE-20",
                        )
                    )

                # Check for unconstrained arrays
                if param_type == "array" and "items" not in param_spec:
                    self.issues.append(
                        SecurityIssue(
                            level=RiskLevel.LOW,
                            category="input_validation",
                            title=f"Unconstrained array parameter: {param_name}",
                            description=f"Array parameter '{param_name}' has no item type validation",
                            location=location,
                            recommendation="Add 'items' schema to validate array contents",
                            cwe_id="CWE-20",
                        )
                    )

                if param_type == "array" and "maxItems" not in param_spec:
                    self.issues.append(
                        SecurityIssue(
                            level=RiskLevel.LOW,
                            category="input_validation",
                            title=f"Unbounded array parameter: {param_name}",
                            description=f"Array parameter '{param_name}' has no size limit, vulnerable to DoS",
                            location=location,
                            recommendation="Add 'maxItems' constraint. Example: \"maxItems\": 100",
                            cwe_id="CWE-770",  # Allocation of Resources Without Limits
                        )
                    )

    def _check_sensitive_data(self, manifest: dict):
        """Check for potential sensitive data exposure."""
        tools = manifest.get("tools", [])

        for i, tool in enumerate(tools):
            desc = (tool.get("description", "") + json.dumps(tool.get("inputSchema", {}))).lower()

            for keyword in self.SENSITIVE_KEYWORDS:
                if keyword in desc:
                    self.issues.append(
                        SecurityIssue(
                            level=RiskLevel.HIGH,
                            category="sensitive_data",
                            title=f"Potential sensitive data handling: {tool.get('name')}",
                            description=f"Tool mentions '{keyword}' which suggests it handles sensitive data",
                            location=f"tools[{i}]",
                            recommendation="Ensure: 1) Sensitive data is encrypted in transit and at rest, 2) Proper authentication/authorization, 3) Audit logging, 4) No sensitive data in logs, 5) Compliance with data protection regulations (GDPR, HIPAA, etc.)",
                            cwe_id="CWE-359",  # Exposure of Private Personal Information
                        )
                    )
                    break

    def _check_risky_parameters(self, manifest: dict):
        """Check for parameters that commonly lead to vulnerabilities."""
        tools = manifest.get("tools", [])

        for i, tool in enumerate(tools):
            schema = tool.get("inputSchema", {})
            properties = schema.get("properties", {})

            for param_name in properties.keys():
                param_lower = param_name.lower()

                # Check for file/path parameters
                if any(keyword in param_lower for keyword in ["path", "file", "dir"]):
                    pattern = properties[param_name].get("pattern")
                    enum_values = properties[param_name].get("enum")
                    # Only flag if neither pattern nor enum is present
                    if not pattern and not enum_values:
                        self.issues.append(
                            SecurityIssue(
                                level=RiskLevel.CRITICAL,
                                category="path_traversal",
                                title=f"Unvalidated file path parameter: {param_name}",
                                description=f"Parameter '{param_name}' in tool '{tool.get('name')}' accepts file paths without validation. This is vulnerable to path traversal attacks (e.g., '../../../etc/passwd')",
                                location=f"tools[{i}].inputSchema.properties.{param_name}",
                                recommendation="Add strict pattern validation to prevent path traversal. Never allow '..' or absolute paths. Example pattern: '^[a-zA-Z0-9_-]+\\.[a-z]{2,4}$'",
                                cwe_id="CWE-22",  # Path Traversal
                            )
                        )

                # Check for URL parameters
                if any(keyword in param_lower for keyword in ["url", "uri", "link"]):
                    pattern = properties[param_name].get("pattern")
                    enum_values = properties[param_name].get("enum")
                    if not pattern and not enum_values:
                        self.issues.append(
                            SecurityIssue(
                                level=RiskLevel.HIGH,
                                category="ssrf",
                                title=f"Unvalidated URL parameter: {param_name}",
                                description=f"Parameter '{param_name}' accepts URLs without validation. This could enable SSRF (Server-Side Request Forgery) attacks",
                                location=f"tools[{i}].inputSchema.properties.{param_name}",
                                recommendation="Validate URLs: 1) Whitelist allowed protocols (http/https only), 2) Block private IP ranges, 3) Use allowlist of allowed domains if possible",
                                cwe_id="CWE-918",  # Server-Side Request Forgery (SSRF)
                            )
                        )

                # Check for SQL/query parameters
                # Only flag if parameter name contains "sql" or tool description mentions SQL/database
                tool_desc = (tool.get("description", "") + tool.get("name", "")).lower()
                is_sql_related = "sql" in tool_desc or "database" in tool_desc or "db" in tool_desc
                if (
                    "sql" in param_lower
                    or "where" in param_lower
                    or (is_sql_related and "query" in param_lower)
                ):
                    self.issues.append(
                        SecurityIssue(
                            level=RiskLevel.CRITICAL,
                            category="injection",
                            title=f"Potential SQL injection: {param_name}",
                            description=f"Parameter '{param_name}' in tool '{tool.get('name')}' appears to accept SQL queries",
                            location=f"tools[{i}].inputSchema.properties.{param_name}",
                            recommendation="NEVER accept raw SQL from users. Use: 1) Parameterized queries, 2) ORM/query builder, 3) Strict whitelist of allowed operations. This schema cannot prevent SQL injection - you must validate in code.",
                            cwe_id="CWE-89",  # SQL Injection
                        )
                    )

                # Check for command parameters
                if any(keyword in param_lower for keyword in ["command", "cmd", "exec", "shell"]):
                    self.issues.append(
                        SecurityIssue(
                            level=RiskLevel.CRITICAL,
                            category="injection",
                            title=f"Potential command injection: {param_name}",
                            description=f"Parameter '{param_name}' in tool '{tool.get('name')}' appears to accept system commands",
                            location=f"tools[{i}].inputSchema.properties.{param_name}",
                            recommendation="NEVER execute user-provided commands. If absolutely necessary: 1) Use strict whitelist of allowed commands, 2) Never use shell=True, 3) Sanitize all inputs, 4) Run in isolated environment with minimal privileges. Consider if this tool should exist at all.",
                            cwe_id="CWE-78",  # OS Command Injection
                        )
                    )

    def _check_capabilities(self, manifest: dict):
        """Check declared capabilities for security implications."""
        capabilities = manifest.get("capabilities", {})

        # Check if resources are subscribable
        resources_cap = capabilities.get("resources", {})
        if resources_cap.get("subscribe"):
            self.issues.append(
                SecurityIssue(
                    level=RiskLevel.INFO,
                    category="capability",
                    title="Resource subscriptions enabled",
                    description="Server supports resource subscriptions, which maintain persistent connections",
                    location="capabilities.resources.subscribe",
                    recommendation="Ensure: 1) Proper authentication for subscriptions, 2) Rate limiting on subscription creation, 3) Maximum subscribers limit enforced, 4) Automatic cleanup of stale subscriptions",
                )
            )

        # Info about capabilities count
        tools_count = len(manifest.get("tools", []))
        if tools_count > 20:
            self.issues.append(
                SecurityIssue(
                    level=RiskLevel.INFO,
                    category="attack_surface",
                    title=f"Large number of tools ({tools_count})",
                    description="Server exposes many tools, increasing attack surface",
                    location="tools",
                    recommendation="Review if all tools are necessary. Follow principle of least privilege - only expose required functionality.",
                )
            )

    def _check_authentication_indicators(self, manifest: dict):
        """Check for indications of authentication/authorization."""
        manifest_str = json.dumps(manifest).lower()

        # Check if authentication is mentioned
        auth_keywords = ["auth", "authentication", "authorization", "token", "api_key"]
        has_auth_mention = any(keyword in manifest_str for keyword in auth_keywords)

        tools = manifest.get("tools", [])
        dangerous_tools_count = sum(
            1
            for tool in tools
            if any(
                keyword in tool.get("name", "").lower() + tool.get("description", "").lower()
                for keyword in self.DANGEROUS_KEYWORDS
            )
        )

        if dangerous_tools_count > 0 and not has_auth_mention:
            self.issues.append(
                SecurityIssue(
                    level=RiskLevel.HIGH,
                    category="authentication",
                    title="No authentication indicators found",
                    description=f"Server exposes {dangerous_tools_count} potentially dangerous tool(s) but manifest contains no mention of authentication or authorization",
                    location="root",
                    recommendation="⚠️ CRITICAL: This validator cannot verify if authentication is properly implemented. You MUST manually verify: 1) Authentication is required for sensitive operations, 2) Authorization checks are in place, 3) Role-based access control is implemented. Manifest validation alone is NOT sufficient for security.",
                    cwe_id="CWE-306",  # Missing Authentication
                )
            )

    def _calculate_risk_score(self) -> int:
        """Calculate overall risk score (0-100)."""
        # Weight by severity
        weights = {
            RiskLevel.CRITICAL: 25,
            RiskLevel.HIGH: 15,
            RiskLevel.MEDIUM: 5,
            RiskLevel.LOW: 2,
            RiskLevel.INFO: 0,
        }

        score = sum(weights[issue.level] for issue in self.issues)

        # Cap at 100
        return min(score, 100)

    def _determine_overall_risk(self, risk_score: int) -> RiskLevel:
        """Determine overall risk level from score."""
        # Any critical issue = critical overall
        if any(issue.level == RiskLevel.CRITICAL for issue in self.issues):
            return RiskLevel.CRITICAL

        # Otherwise use score thresholds
        if risk_score >= 75:
            return RiskLevel.CRITICAL
        elif risk_score >= 50:
            return RiskLevel.HIGH
        elif risk_score >= 25:
            return RiskLevel.MEDIUM
        elif risk_score > 0:
            return RiskLevel.LOW
        else:
            return RiskLevel.INFO


def validate_manifest(manifest: dict | str | Path) -> tuple[ValidationResult, RiskAssessment]:
    """
    Convenience function to validate a manifest and assess risk.

    Args:
        manifest: Manifest dictionary, JSON string, or file path

    Returns:
        Tuple of (ValidationResult, RiskAssessment)

    Example:
        result, assessment = validate_manifest("manifest.json")
        if not result.valid:
            print("Invalid manifest:", result.errors)
        if assessment.overall_risk in (RiskLevel.CRITICAL, RiskLevel.HIGH):
            print("High security risk - manual review required")
    """
    validator = ManifestValidator()

    # Validate structure
    if isinstance(manifest, dict):
        result = validator.validate(manifest)
    elif isinstance(manifest, str):
        # Check if it's a JSON string or file path
        manifest_str = manifest.strip()
        if manifest_str.startswith("{") or manifest_str.startswith("["):
            # It's a JSON string - parse it
            try:
                manifest_dict = json.loads(manifest_str)
                result = validator.validate(manifest_dict)
            except json.JSONDecodeError as e:
                result = ValidationResult(valid=False, errors=[f"Invalid JSON: {e}"])
        else:
            # It's a file path
            result = validator.validate_file(manifest)
    else:
        result = validator.validate_file(manifest)

    # Assess risk
    if result.valid and result.manifest:
        assessment = validator.assess_risk(result.manifest)
    else:
        # Can't assess risk if manifest is invalid
        assessment = RiskAssessment(
            overall_risk=RiskLevel.CRITICAL,
            risk_score=100,
            issues=[
                SecurityIssue(
                    level=RiskLevel.CRITICAL,
                    category="validation",
                    title="Invalid manifest structure",
                    description="Manifest failed structural validation",
                    location="root",
                    recommendation="Fix validation errors before deploying",
                )
            ],
            summary={"critical": 1, "high": 0, "medium": 0, "low": 0, "info": 0},
        )

    return result, assessment
