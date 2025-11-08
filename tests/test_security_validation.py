"""
Tests for security validation functionality.
"""

import json

from nextmcp.security import (
    ManifestValidator,
    RiskAssessment,
    RiskLevel,
    SecurityIssue,
)
from nextmcp.security.validation import validate_manifest


class TestManifestValidator:
    """Tests for ManifestValidator class."""

    def test_valid_minimal_manifest(self):
        """Test validation of a minimal valid manifest."""
        manifest = {
            "mcpVersion": "2025-06-18",
            "implementation": {"name": "test-server", "version": "1.0.0"},
            "capabilities": {},
        }

        validator = ManifestValidator()
        result = validator.validate(manifest)

        assert result.valid
        assert len(result.errors) == 0

    def test_missing_implementation(self):
        """Test validation fails with missing implementation."""
        manifest = {"mcpVersion": "2025-06-18"}

        validator = ManifestValidator()
        result = validator.validate(manifest)

        assert not result.valid
        assert "Missing required field: implementation" in result.errors

    def test_missing_implementation_fields(self):
        """Test validation fails with incomplete implementation."""
        manifest = {"implementation": {"name": "test"}}  # Missing version

        validator = ManifestValidator()
        result = validator.validate(manifest)

        assert not result.valid
        assert any("implementation.version" in error for error in result.errors)

    def test_validate_file_not_found(self, tmp_path):
        """Test validation of non-existent file."""
        validator = ManifestValidator()
        result = validator.validate_file(tmp_path / "nonexistent.json")

        assert not result.valid
        assert "not found" in result.errors[0].lower()

    def test_validate_invalid_json(self, tmp_path):
        """Test validation of malformed JSON."""
        manifest_file = tmp_path / "bad.json"
        manifest_file.write_text("{ invalid json }")

        validator = ManifestValidator()
        result = validator.validate_file(manifest_file)

        assert not result.valid
        assert "Invalid JSON" in result.errors[0]

    def test_tools_not_array(self):
        """Test validation fails when tools is not an array."""
        manifest = {
            "implementation": {"name": "test", "version": "1.0.0"},
            "tools": "not an array",
        }

        validator = ManifestValidator()
        result = validator.validate(manifest)

        assert not result.valid
        assert "tools' must be an array" in result.errors[0]


class TestRiskAssessment:
    """Tests for risk assessment functionality."""

    def test_safe_manifest_low_risk(self):
        """Test that a safe manifest gets low risk score."""
        manifest = {
            "implementation": {"name": "safe-server", "version": "1.0.0"},
            "tools": [
                {
                    "name": "get_info",
                    "description": "Get information",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "maxLength": 100,
                                "pattern": "^[a-zA-Z0-9 ]+$",
                            }
                        },
                    },
                }
            ],
        }

        validator = ManifestValidator()
        assessment = validator.assess_risk(manifest)

        assert assessment.risk_score < 50
        assert assessment.overall_risk in (RiskLevel.LOW, RiskLevel.INFO, RiskLevel.MEDIUM)

    def test_dangerous_tool_name(self):
        """Test detection of dangerous tool names."""
        manifest = {
            "implementation": {"name": "dangerous-server", "version": "1.0.0"},
            "tools": [
                {
                    "name": "delete_everything",
                    "description": "Delete all data",
                    "inputSchema": {"type": "object", "properties": {}},
                }
            ],
        }

        validator = ManifestValidator()
        assessment = validator.assess_risk(manifest)

        # Should detect dangerous operation
        assert any(
            issue.category == "dangerous_operation" and issue.level == RiskLevel.HIGH
            for issue in assessment.issues
        )
        assert assessment.risk_score > 0

    def test_unbounded_string_parameter(self):
        """Test detection of unbounded string parameters."""
        manifest = {
            "implementation": {"name": "test", "version": "1.0.0"},
            "tools": [
                {
                    "name": "process_data",
                    "description": "Process data",
                    "inputSchema": {
                        "type": "object",
                        "properties": {"data": {"type": "string"}},  # No maxLength!
                    },
                }
            ],
        }

        validator = ManifestValidator()
        assessment = validator.assess_risk(manifest)

        assert any(
            "Unbounded string" in issue.title and issue.level == RiskLevel.MEDIUM
            for issue in assessment.issues
        )

    def test_path_traversal_risk(self):
        """Test detection of unvalidated file path parameters."""
        manifest = {
            "implementation": {"name": "test", "version": "1.0.0"},
            "tools": [
                {
                    "name": "read_file",
                    "description": "Read a file",
                    "inputSchema": {
                        "type": "object",
                        "properties": {"file_path": {"type": "string"}},  # No pattern validation!
                    },
                }
            ],
        }

        validator = ManifestValidator()
        assessment = validator.assess_risk(manifest)

        # Should detect path traversal risk
        assert any(
            issue.category == "path_traversal" and issue.level == RiskLevel.CRITICAL
            for issue in assessment.issues
        )

    def test_sql_injection_risk(self):
        """Test detection of SQL query parameters."""
        manifest = {
            "implementation": {"name": "test", "version": "1.0.0"},
            "tools": [
                {
                    "name": "execute_query",
                    "description": "Execute SQL query",
                    "inputSchema": {
                        "type": "object",
                        "properties": {"query": {"type": "string"}},
                    },
                }
            ],
        }

        validator = ManifestValidator()
        assessment = validator.assess_risk(manifest)

        # Should detect SQL injection risk
        assert any(
            issue.category == "injection"
            and "SQL injection" in issue.title
            and issue.level == RiskLevel.CRITICAL
            for issue in assessment.issues
        )

    def test_command_injection_risk(self):
        """Test detection of command parameters."""
        manifest = {
            "implementation": {"name": "test", "version": "1.0.0"},
            "tools": [
                {
                    "name": "run_command",
                    "description": "Run system command",
                    "inputSchema": {
                        "type": "object",
                        "properties": {"command": {"type": "string"}},
                    },
                }
            ],
        }

        validator = ManifestValidator()
        assessment = validator.assess_risk(manifest)

        # Should detect command injection risk
        assert any(
            issue.category == "injection"
            and "command injection" in issue.title.lower()
            and issue.level == RiskLevel.CRITICAL
            for issue in assessment.issues
        )

    def test_ssrf_risk(self):
        """Test detection of unvalidated URL parameters."""
        manifest = {
            "implementation": {"name": "test", "version": "1.0.0"},
            "tools": [
                {
                    "name": "fetch_url",
                    "description": "Fetch data from URL",
                    "inputSchema": {
                        "type": "object",
                        "properties": {"url": {"type": "string"}},
                    },
                }
            ],
        }

        validator = ManifestValidator()
        assessment = validator.assess_risk(manifest)

        # Should detect SSRF risk
        assert any(
            issue.category == "ssrf" and issue.level == RiskLevel.HIGH
            for issue in assessment.issues
        )

    def test_sensitive_data_detection(self):
        """Test detection of sensitive data keywords."""
        manifest = {
            "implementation": {"name": "test", "version": "1.0.0"},
            "tools": [
                {
                    "name": "authenticate",
                    "description": "Authenticate user with password",
                    "inputSchema": {
                        "type": "object",
                        "properties": {"password": {"type": "string"}},
                    },
                }
            ],
        }

        validator = ManifestValidator()
        assessment = validator.assess_risk(manifest)

        # Should detect sensitive data
        assert any(
            issue.category == "sensitive_data" and issue.level == RiskLevel.HIGH
            for issue in assessment.issues
        )

    def test_unconstrained_object_parameter(self):
        """Test detection of objects without property definitions."""
        manifest = {
            "implementation": {"name": "test", "version": "1.0.0"},
            "tools": [
                {
                    "name": "process",
                    "description": "Process data",
                    "inputSchema": {
                        "type": "object",
                        "properties": {"data": {"type": "object"}},  # No properties defined!
                    },
                }
            ],
        }

        validator = ManifestValidator()
        assessment = validator.assess_risk(manifest)

        assert any(
            "Unconstrained object" in issue.title and issue.level == RiskLevel.MEDIUM
            for issue in assessment.issues
        )

    def test_unbounded_array_parameter(self):
        """Test detection of arrays without size limits."""
        manifest = {
            "implementation": {"name": "test", "version": "1.0.0"},
            "tools": [
                {
                    "name": "batch_process",
                    "description": "Process batch",
                    "inputSchema": {
                        "type": "object",
                        "properties": {"items": {"type": "array"}},  # No maxItems!
                    },
                }
            ],
        }

        validator = ManifestValidator()
        assessment = validator.assess_risk(manifest)

        assert any(
            "Unbounded array" in issue.title and issue.level == RiskLevel.LOW
            for issue in assessment.issues
        )

    def test_large_tool_count(self):
        """Test warning for large number of tools."""
        tools = [
            {
                "name": f"tool_{i}",
                "description": "Test tool",
                "inputSchema": {"type": "object", "properties": {}},
            }
            for i in range(25)
        ]

        manifest = {
            "implementation": {"name": "test", "version": "1.0.0"},
            "tools": tools,
        }

        validator = ManifestValidator()
        assessment = validator.assess_risk(manifest)

        # Should have info about large attack surface
        assert any(
            issue.category == "attack_surface" and issue.level == RiskLevel.INFO
            for issue in assessment.issues
        )

    def test_no_authentication_indicators(self):
        """Test detection of missing authentication indicators."""
        manifest = {
            "implementation": {"name": "test", "version": "1.0.0"},
            "tools": [
                {
                    "name": "delete_user",  # Dangerous operation
                    "description": "Delete a user",
                    "inputSchema": {"type": "object", "properties": {}},
                }
            ],
        }

        validator = ManifestValidator()
        assessment = validator.assess_risk(manifest)

        # Should warn about missing auth indicators
        assert any(
            issue.category == "authentication" and issue.level == RiskLevel.HIGH
            for issue in assessment.issues
        )

    def test_risk_score_calculation(self):
        """Test risk score calculation with multiple issues."""
        manifest = {
            "implementation": {"name": "risky-server", "version": "1.0.0"},
            "tools": [
                {
                    "name": "delete_database",
                    "description": "Execute SQL command",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "sql": {"type": "string"},
                            "file_path": {"type": "string"},
                        },
                    },
                }
            ],
        }

        validator = ManifestValidator()
        assessment = validator.assess_risk(manifest)

        # Should have high risk score due to multiple critical issues
        assert assessment.risk_score > 50
        assert assessment.overall_risk in (RiskLevel.CRITICAL, RiskLevel.HIGH)

    def test_overall_risk_critical_with_critical_issue(self):
        """Test that any critical issue makes overall risk critical."""
        manifest = {
            "implementation": {"name": "test", "version": "1.0.0"},
            "tools": [
                {
                    "name": "read_file",
                    "description": "Read file",
                    "inputSchema": {
                        "type": "object",
                        "properties": {"path": {"type": "string"}},
                    },
                }
            ],
        }

        validator = ManifestValidator()
        assessment = validator.assess_risk(manifest)

        # Path parameter without validation = critical
        assert assessment.overall_risk == RiskLevel.CRITICAL

    def test_summary_counts(self):
        """Test that issue summary counts are accurate."""
        manifest = {
            "implementation": {"name": "test", "version": "1.0.0"},
            "tools": [
                {
                    "name": "dangerous_tool",
                    "description": "Delete files",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "path": {"type": "string"},  # CRITICAL: path traversal
                            "data": {"type": "string"},  # MEDIUM: unbounded string
                        },
                    },
                }
            ],
        }

        validator = ManifestValidator()
        assessment = validator.assess_risk(manifest)

        # Check summary has correct counts
        total = sum(assessment.summary.values())
        assert total == len(assessment.issues)
        assert assessment.summary["critical"] > 0

    def test_cwe_ids_present(self):
        """Test that CWE IDs are assigned to issues."""
        manifest = {
            "implementation": {"name": "test", "version": "1.0.0"},
            "tools": [
                {
                    "name": "sql_query",
                    "description": "Run query",
                    "inputSchema": {
                        "type": "object",
                        "properties": {"query": {"type": "string"}},
                    },
                }
            ],
        }

        validator = ManifestValidator()
        assessment = validator.assess_risk(manifest)

        # SQL injection should have CWE-89
        sql_issue = next((issue for issue in assessment.issues if "SQL" in issue.title), None)
        assert sql_issue is not None
        assert sql_issue.cwe_id == "CWE-89"


class TestSecurityIssue:
    """Tests for SecurityIssue dataclass."""

    def test_to_dict(self):
        """Test conversion to dictionary."""
        issue = SecurityIssue(
            level=RiskLevel.HIGH,
            category="test",
            title="Test Issue",
            description="Test description",
            location="tools[0]",
            recommendation="Fix it",
            cwe_id="CWE-123",
        )

        d = issue.to_dict()

        assert d["level"] == "high"
        assert d["category"] == "test"
        assert d["title"] == "Test Issue"
        assert d["cwe_id"] == "CWE-123"


class TestRiskAssessmentDataclass:
    """Tests for RiskAssessment dataclass."""

    def test_to_dict(self):
        """Test conversion to dictionary."""
        issue = SecurityIssue(
            level=RiskLevel.MEDIUM,
            category="test",
            title="Test",
            description="Desc",
            location="loc",
            recommendation="Rec",
        )

        assessment = RiskAssessment(
            overall_risk=RiskLevel.MEDIUM,
            risk_score=42,
            issues=[issue],
            summary={"critical": 0, "high": 0, "medium": 1, "low": 0, "info": 0},
        )

        d = assessment.to_dict()

        assert d["overall_risk"] == "medium"
        assert d["risk_score"] == 42
        assert len(d["issues"]) == 1
        assert d["summary"]["medium"] == 1


class TestValidateManifestFunction:
    """Tests for the validate_manifest convenience function."""

    def test_validate_from_dict(self):
        """Test validation from dictionary."""
        manifest = {
            "implementation": {"name": "test", "version": "1.0.0"},
            "tools": [],
        }

        result, assessment = validate_manifest(manifest)

        assert result.valid
        assert isinstance(assessment, RiskAssessment)

    def test_validate_from_json_string(self):
        """Test validation from JSON string."""
        manifest_json = '{"implementation": {"name": "test", "version": "1.0.0"}}'

        result, assessment = validate_manifest(manifest_json)

        assert result.valid

    def test_validate_from_file(self, tmp_path):
        """Test validation from file."""
        manifest = {
            "implementation": {"name": "test", "version": "1.0.0"},
            "tools": [],
        }

        manifest_file = tmp_path / "manifest.json"
        with open(manifest_file, "w") as f:
            json.dump(manifest, f)

        result, assessment = validate_manifest(manifest_file)

        assert result.valid

    def test_invalid_manifest_gets_critical_risk(self):
        """Test that invalid manifests get critical risk assessment."""
        result, assessment = validate_manifest({"invalid": "manifest"})

        assert not result.valid
        assert assessment.overall_risk == RiskLevel.CRITICAL
        assert assessment.risk_score == 100


class TestComplexScenarios:
    """Tests for complex real-world scenarios."""

    def test_well_secured_manifest(self):
        """Test a well-secured manifest with proper validation."""
        manifest = {
            "implementation": {
                "name": "secure-server",
                "version": "1.0.0",
                "description": "A secure server with authentication",
            },
            "capabilities": {"tools": {"listChanged": True}, "logging": {}},
            "tools": [
                {
                    "name": "get_user",
                    "description": "Get user information (requires authentication)",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "user_id": {
                                "type": "string",
                                "pattern": "^[a-zA-Z0-9-]{36}$",  # UUID
                                "description": "User UUID",
                            }
                        },
                        "required": ["user_id"],
                    },
                },
                {
                    "name": "list_files",
                    "description": "List files in allowed directory",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "directory": {
                                "type": "string",
                                "enum": ["documents", "images", "downloads"],
                                "description": "Allowed directory",
                            }
                        },
                        "required": ["directory"],
                    },
                },
            ],
        }

        validator = ManifestValidator()
        assessment = validator.assess_risk(manifest)

        # Should have low/medium risk due to proper validation
        assert assessment.overall_risk in (
            RiskLevel.LOW,
            RiskLevel.MEDIUM,
            RiskLevel.INFO,
        )
        assert assessment.risk_score < 50

    def test_worst_case_manifest(self):
        """Test a worst-case scenario manifest."""
        manifest = {
            "implementation": {"name": "insecure-server", "version": "0.1.0"},
            "tools": [
                {
                    "name": "execute_command",
                    "description": "Execute system command with password",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "command": {"type": "string"},
                            "sql_query": {"type": "string"},
                            "file_path": {"type": "string"},
                            "url": {"type": "string"},
                            "password": {"type": "string"},
                        },
                    },
                },
                {
                    "name": "delete_database",
                    "description": "Drop all tables",
                    "inputSchema": {"type": "object", "properties": {}},
                },
            ],
        }

        validator = ManifestValidator()
        assessment = validator.assess_risk(manifest)

        # Should have maximum risk
        assert assessment.overall_risk == RiskLevel.CRITICAL
        assert assessment.risk_score >= 75
        assert assessment.summary["critical"] >= 3
        assert len(assessment.issues) >= 5

    def test_manifest_from_real_server(self, tmp_path):
        """Test validation of a manifest from a real server."""
        # Simulate manifest generated from actual server
        manifest = {
            "mcpVersion": "2025-06-18",
            "implementation": {
                "name": "blog-server",
                "version": "1.0.0",
                "description": "Blog management server",
            },
            "capabilities": {"tools": {"listChanged": True}, "logging": {}},
            "tools": [
                {
                    "name": "create_post",
                    "description": "Create a new blog post",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "title": {
                                "type": "string",
                                "maxLength": 200,
                                "description": "Post title",
                            },
                            "content": {
                                "type": "string",
                                "maxLength": 10000,
                                "description": "Post content",
                            },
                        },
                        "required": ["title", "content"],
                    },
                },
                {
                    "name": "delete_post",
                    "description": "Delete a blog post (requires admin)",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "post_id": {
                                "type": "integer",
                                "minimum": 1,
                                "description": "Post ID",
                            }
                        },
                        "required": ["post_id"],
                    },
                },
            ],
            "metadata": {
                "generatedAt": "2025-11-07T00:00:00Z",
                "generatedBy": "nextmcp",
            },
        }

        manifest_file = tmp_path / "blog-manifest.json"
        with open(manifest_file, "w") as f:
            json.dump(manifest, f, indent=2)

        result, assessment = validate_manifest(manifest_file)

        assert result.valid
        # Should flag delete_post as dangerous but overall moderate risk
        assert any(issue.category == "dangerous_operation" for issue in assessment.issues)
        assert assessment.overall_risk in (RiskLevel.MEDIUM, RiskLevel.HIGH)
