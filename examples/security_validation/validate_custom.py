"""
Example: Custom validation script for CI/CD integration.

This script demonstrates how to:
- Programmatically validate manifests
- Filter issues by severity
- Generate security reports
- Integrate with CI/CD pipelines
"""

import json
import sys

from nextmcp.security import ManifestValidator, RiskLevel


def validate_manifest_file(manifest_path: str, fail_on_level: RiskLevel = RiskLevel.CRITICAL):
    """
    Validate a manifest file and return detailed results.

    Args:
        manifest_path: Path to manifest.json
        fail_on_level: Fail if risk is at this level or above

    Returns:
        Tuple of (passed: bool, report: dict)
    """
    validator = ManifestValidator()

    print(f"🔍 Validating: {manifest_path}")
    print("=" * 60)

    # Validate structure
    result = validator.validate_file(manifest_path)

    if not result.valid:
        print("❌ FAILED: Invalid manifest structure\n")
        print("Errors:")
        for error in result.errors:
            print(f"  - {error}")
        return False, {"valid": False, "errors": result.errors}

    print("✅ Manifest structure is valid\n")

    # Assess security risks
    assessment = validator.assess_risk(manifest_path)

    # Generate report
    report = {
        "manifest": manifest_path,
        "valid": True,
        "risk_level": assessment.overall_risk.value,
        "risk_score": assessment.risk_score,
        "summary": assessment.summary,
        "issues": [
            {
                "level": issue.level.value,
                "category": issue.category,
                "title": issue.title,
                "location": issue.location,
                "cwe": issue.cwe_id,
            }
            for issue in assessment.issues
        ],
    }

    # Print summary
    print("📊 Security Assessment:")
    print(f"  Risk Level: {assessment.overall_risk.value.upper()}")
    print(f"  Risk Score: {assessment.risk_score}/100")
    print()

    print("📋 Issue Summary:")
    print(f"  Critical: {assessment.summary['critical']}")
    print(f"  High:     {assessment.summary['high']}")
    print(f"  Medium:   {assessment.summary['medium']}")
    print(f"  Low:      {assessment.summary['low']}")
    print(f"  Info:     {assessment.summary['info']}")
    print()

    # Detailed issues by category
    if assessment.issues:
        print("🔍 Issues by Category:")
        by_category = {}
        for issue in assessment.issues:
            if issue.category not in by_category:
                by_category[issue.category] = []
            by_category[issue.category].append(issue)

        for category, issues in sorted(by_category.items()):
            print(f"\n  {category.upper()}:")
            for issue in issues:
                print(f"    [{issue.level.value}] {issue.title}")

    print("\n" + "=" * 60)

    # Determine pass/fail
    risk_order = [
        RiskLevel.INFO,
        RiskLevel.LOW,
        RiskLevel.MEDIUM,
        RiskLevel.HIGH,
        RiskLevel.CRITICAL,
    ]
    fail_threshold = risk_order.index(fail_on_level)
    actual_level = risk_order.index(assessment.overall_risk)

    passed = actual_level < fail_threshold

    if passed:
        print(f"✅ PASSED: Risk level acceptable (threshold: {fail_on_level.value})")
    else:
        print(f"❌ FAILED: Risk level too high (threshold: {fail_on_level.value})")

    return passed, report


def generate_security_report(report: dict, output_file: str):
    """Generate a JSON security report for CI/CD."""
    with open(output_file, "w") as f:
        json.dump(report, f, indent=2)
    print(f"\n📄 Security report saved to: {output_file}")


def compare_manifests(manifest1: str, manifest2: str):
    """Compare two manifests and show risk changes."""
    print("🔄 Comparing manifests...")
    print(f"  Before: {manifest1}")
    print(f"  After:  {manifest2}")
    print()

    validator = ManifestValidator()

    assessment1 = validator.assess_risk(manifest1)
    assessment2 = validator.assess_risk(manifest2)

    print("📊 Risk Comparison:")
    print(f"  Before: {assessment1.overall_risk.value.upper()} (score: {assessment1.risk_score})")
    print(f"  After:  {assessment2.overall_risk.value.upper()} (score: {assessment2.risk_score})")

    score_change = assessment2.risk_score - assessment1.risk_score
    if score_change > 0:
        print(f"  ⚠️  Risk increased by {score_change} points")
    elif score_change < 0:
        print(f"  ✅ Risk decreased by {abs(score_change)} points")
    else:
        print("  → No change in risk score")

    print("\n📋 Issue Changes:")
    for level in ["critical", "high", "medium", "low"]:
        before = assessment1.summary[level]
        after = assessment2.summary[level]
        if before != after:
            change = after - before
            symbol = "+" if change > 0 else ""
            print(f"  {level.capitalize()}: {before} → {after} ({symbol}{change})")


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Validate MCP manifest for security issues")
    parser.add_argument("manifest", help="Path to manifest.json file")
    parser.add_argument(
        "--fail-on",
        choices=["critical", "high", "medium", "low"],
        default="critical",
        help="Fail if risk is at this level or above",
    )
    parser.add_argument(
        "--report",
        help="Save security report to JSON file",
    )
    parser.add_argument(
        "--compare",
        help="Compare with another manifest",
    )

    args = parser.parse_args()

    # Map string to RiskLevel
    fail_levels = {
        "critical": RiskLevel.CRITICAL,
        "high": RiskLevel.HIGH,
        "medium": RiskLevel.MEDIUM,
        "low": RiskLevel.LOW,
    }

    # Validate manifest
    passed, report = validate_manifest_file(args.manifest, fail_levels[args.fail_on])

    # Save report if requested
    if args.report:
        generate_security_report(report, args.report)

    # Compare if requested
    if args.compare:
        print("\n")
        compare_manifests(args.manifest, args.compare)

    # Exit with appropriate code
    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    # Example usage without command line args
    if len(sys.argv) == 1:
        print("Custom Validation Example")
        print("=" * 60)
        print()

        # Example 1: Validate a manifest
        print("Example 1: Basic Validation")
        print("-" * 60)

        # Create a test manifest
        test_manifest = {
            "implementation": {"name": "test-server", "version": "1.0.0"},
            "tools": [
                {
                    "name": "read_file",
                    "description": "Read a file",
                    "inputSchema": {
                        "type": "object",
                        "properties": {"path": {"type": "string"}},
                    },
                }
            ],
        }

        with open("test_manifest.json", "w") as f:
            json.dump(test_manifest, f)

        passed, report = validate_manifest_file("test_manifest.json", RiskLevel.HIGH)

        print("\n" + "=" * 60)
        print("\nTo run with custom options:")
        print("  python validate_custom.py manifest.json")
        print("  python validate_custom.py manifest.json --fail-on high")
        print("  python validate_custom.py manifest.json --report security-report.json")
        print("  python validate_custom.py manifest.json --compare old-manifest.json")
    else:
        main()
