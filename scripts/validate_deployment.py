#!/usr/bin/env python3
"""
Deployment Validation Script

Verifies that all required files, configurations, and dependencies are ready
for AWS deployment. Run this before `cdk deploy` to catch issues early.

Usage:
    python scripts/validate_deployment.py

Exit codes:
    0 - All checks passed, ready for deployment
    1 - One or more checks failed, review output
"""

import sys
import json
import os
from pathlib import Path
from typing import List, Tuple, Dict, Any
import subprocess

# ANSI color codes for terminal output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'
BOLD = '\033[1m'

# Track validation results
checks_passed = 0
checks_failed = 0
checks_warned = 0


def print_header(title: str):
    """Print section header."""
    print(f"\n{BLUE}{BOLD}{'=' * 80}{RESET}")
    print(f"{BLUE}{BOLD}{title:^80}{RESET}")
    print(f"{BLUE}{BOLD}{'=' * 80}{RESET}\n")


def print_check(name: str, passed: bool, details: str = ""):
    """Print check result."""
    global checks_passed, checks_failed

    if passed:
        print(f"{GREEN}✓{RESET} {name}")
        checks_passed += 1
    else:
        print(f"{RED}✗{RESET} {name}")
        checks_failed += 1

    if details:
        print(f"  {details}")


def print_warning(name: str, details: str = ""):
    """Print warning (not a failure)."""
    global checks_warned
    print(f"{YELLOW}⚠{RESET} {name}")
    checks_warned += 1
    if details:
        print(f"  {details}")


def check_file_exists(file_path: Path, description: str) -> bool:
    """Check if a required file exists."""
    exists = file_path.exists()
    print_check(
        f"{description}: {file_path}",
        exists,
        "" if exists else f"File not found"
    )
    return exists


def check_json_valid(file_path: Path, description: str) -> Tuple[bool, Any]:
    """Check if JSON file exists and is valid."""
    if not file_path.exists():
        print_check(f"{description}: {file_path}", False, "File not found")
        return False, None

    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
        print_check(f"{description}: {file_path}", True)
        return True, data
    except json.JSONDecodeError as e:
        print_check(f"{description}: {file_path}", False, f"Invalid JSON: {e}")
        return False, None


def validate_project_structure():
    """Validate that all required directories and files exist."""
    print_header("PROJECT STRUCTURE")

    root = Path.cwd()

    # Required directories
    required_dirs = [
        ('lambda', 'Lambda functions directory'),
        ('lambda_api', 'API handlers directory'),
        ('frontend', 'Frontend application directory'),
        ('infra', 'CDK infrastructure directory'),
        ('config', 'Configuration files directory'),
        ('tests', 'Test files directory'),
        ('Documentation', 'Documentation directory'),
    ]

    for dir_name, description in required_dirs:
        dir_path = root / dir_name
        check_file_exists(dir_path, f"{description}")

    # Required root files
    required_files = [
        ('app.py', 'CDK app entry point'),
        ('cdk.json', 'CDK configuration'),
        ('requirements.txt', 'Python dependencies'),
        ('pytest.ini', 'Pytest configuration'),
        ('README.md', 'Project README'),
    ]

    for file_name, description in required_files:
        file_path = root / file_name
        check_file_exists(file_path, f"{description}")


def validate_lambda_code():
    """Validate Lambda function code."""
    print_header("LAMBDA FUNCTIONS")

    root = Path.cwd()
    lambda_dir = root / 'lambda'

    # Required Lambda files
    required_files = [
        'handler.py',
        'anthropic_client.py',
        'dynamodb_helper.py',
        'email_formatter.py',
        'output_validator.py',
        'quote_loader.py',
        'quote_tracker.py',
        'security.py',
        'security_alerting.py',
        'security_logging.py',
        'themes.py',
        'requirements.txt',
    ]

    for file_name in required_files:
        check_file_exists(lambda_dir / file_name, f"Lambda: {file_name}")


def validate_api_code():
    """Validate API handler code."""
    print_header("API HANDLERS")

    root = Path.cwd()
    api_dir = root / 'lambda_api'

    required_files = [
        'user_api.py',
        'reflections_api.py',
        'journal_api.py',
        'dynamodb_operations.py',
        'api_utils.py',
        'security.py',
    ]

    for file_name in required_files:
        check_file_exists(api_dir / file_name, f"API: {file_name}")


def validate_frontend():
    """Validate frontend application."""
    print_header("FRONTEND APPLICATION")

    root = Path.cwd()
    frontend_dir = root / 'frontend'

    required_files = [
        'package.json',
        'vite.config.ts',
        'tsconfig.json',
        'amplify.yml',
        'deploy.sh',
        '.env.example',
    ]

    for file_name in required_files:
        check_file_exists(frontend_dir / file_name, f"Frontend: {file_name}")

    # Check for src directory structure
    src_dir = frontend_dir / 'src'
    if src_dir.exists():
        required_src_dirs = ['pages', 'components', 'contexts', 'utils', 'types']
        for dir_name in required_src_dirs:
            dir_path = src_dir / dir_name
            if dir_path.exists():
                print_check(f"Frontend src/{dir_name}", True)
            else:
                print_warning(f"Frontend src/{dir_name}", "Directory not found (may be optional)")


def validate_infrastructure():
    """Validate CDK infrastructure code."""
    print_header("INFRASTRUCTURE (CDK)")

    root = Path.cwd()

    check_file_exists(root / 'app.py', "CDK app entry point")
    check_file_exists(root / 'infra' / 'stoic_stack.py', "CDK stack definition")

    # Validate cdk.json
    valid, cdk_config = check_json_valid(root / 'cdk.json', "CDK configuration")

    if valid and cdk_config:
        # Check for required context variables
        context = cdk_config.get('context', {})
        required_context = [
            'anthropic_api_key',
            'sender_email',
            'sender_domain',
            's3_bucket_prefix',
        ]

        for key in required_context:
            if key in context:
                print_check(f"CDK context: {key}", True, f"Value: {context[key]}")
            else:
                print_warning(f"CDK context: {key}", "Not set (may use default)")


def validate_configuration():
    """Validate configuration files."""
    print_header("CONFIGURATION FILES")

    root = Path.cwd()
    config_dir = root / 'config'

    # Validate quotes database
    valid, quotes_data = check_json_valid(
        config_dir / 'stoic_quotes_365_days.json',
        "Quotes database"
    )

    if valid and quotes_data:
        # Quotes are organized by month: {"january": [...], "february": [...], ...}
        months = ['january', 'february', 'march', 'april', 'may', 'june',
                  'july', 'august', 'september', 'october', 'november', 'december']

        quote_count = 0
        for month in months:
            if month in quotes_data:
                quote_count += len(quotes_data[month])

        if quote_count >= 365:
            print_check(f"Quotes database entries", True, f"Found {quote_count} quotes")
        else:
            print_check(f"Quotes database entries", False, f"Only {quote_count} quotes (need 365)")

    # Validate security config
    valid, security_config = check_json_valid(
        config_dir / 'security_config.json',
        "Security configuration"
    )

    if valid and security_config:
        required_sections = ['content_limits', 'malicious_patterns', 'url_detection', 'sanitization']
        for section in required_sections:
            if section in security_config:
                print_check(f"Security config: {section}", True)
            else:
                print_check(f"Security config: {section}", False, "Section missing")


def validate_tests():
    """Validate test suite."""
    print_header("TEST SUITE")

    root = Path.cwd()
    tests_dir = root / 'tests'

    # Count test files
    test_files = list(tests_dir.rglob('test_*.py'))
    test_count = len(test_files)

    if test_count >= 15:
        print_check(f"Test files", True, f"Found {test_count} test files")
    else:
        print_warning(f"Test files", f"Only {test_count} test files (expected 15+)")

    # Check for conftest.py
    check_file_exists(tests_dir / 'conftest.py', "Pytest fixtures (conftest.py)")

    # Check pytest.ini
    check_file_exists(root / 'pytest.ini', "Pytest configuration")


def validate_documentation():
    """Validate documentation."""
    print_header("DOCUMENTATION")

    root = Path.cwd()
    docs_dir = root / 'Documentation'

    required_docs = [
        'MIGRATION_PLAN.md',
        'PHASE1_SETUP_GUIDE.md',
        'PHASE2_SETUP_GUIDE.md',
        'PHASE4_FRONTEND_GUIDE.md',
        'PHASE5_DEPLOYMENT_MONITORING.md',
        'SECURITY_AUDIT.md',
        'API_EFFICIENCY_ARCHITECTURE.md',
    ]

    for doc_file in required_docs:
        check_file_exists(docs_dir / doc_file, f"Documentation: {doc_file}")


def validate_dependencies():
    """Validate Python dependencies."""
    print_header("PYTHON DEPENDENCIES")

    root = Path.cwd()
    requirements_file = root / 'requirements.txt'

    if not requirements_file.exists():
        print_check("requirements.txt", False, "File not found")
        return

    # Read requirements
    with open(requirements_file, 'r') as f:
        requirements = [line.strip() for line in f if line.strip() and not line.startswith('#')]

    # Check for critical dependencies
    critical_deps = [
        'aws-cdk-lib',
        'boto3',
        'anthropic',
        'pytest',
    ]

    for dep in critical_deps:
        found = any(dep in req for req in requirements)
        print_check(f"Dependency: {dep}", found, "" if found else "Not found in requirements.txt")


def validate_cicd():
    """Validate CI/CD workflows."""
    print_header("CI/CD WORKFLOWS")

    root = Path.cwd()
    workflows_dir = root / '.github' / 'workflows'

    if not workflows_dir.exists():
        print_warning("GitHub workflows directory", "Not found (CI/CD may not be configured)")
        return

    required_workflows = [
        'ci.yml',
        'deploy.yml',
    ]

    for workflow_file in required_workflows:
        check_file_exists(workflows_dir / workflow_file, f"Workflow: {workflow_file}")


def validate_cdk_synth():
    """Attempt CDK synth to validate infrastructure code."""
    print_header("CDK SYNTHESIS")

    try:
        print("Running `cdk synth` to validate infrastructure code...")
        print("(This may take 30-60 seconds)\n")

        result = subprocess.run(
            ['cdk', 'synth'],
            capture_output=True,
            text=True,
            timeout=120
        )

        if result.returncode == 0:
            print_check("CDK synth", True, "Infrastructure code is valid")

            # Check for outputs in synth
            if 'Resources' in result.stdout:
                print("  ✓ CloudFormation template generated successfully")
        else:
            print_check("CDK synth", False, f"Failed with error:\n{result.stderr[:500]}")

    except FileNotFoundError:
        print_warning("CDK synth", "CDK CLI not found (install with: npm install -g aws-cdk)")
    except subprocess.TimeoutExpired:
        print_warning("CDK synth", "Timed out after 120 seconds")
    except Exception as e:
        print_warning("CDK synth", f"Could not run: {e}")


def validate_python_syntax():
    """Validate Python syntax for all Python files."""
    print_header("PYTHON SYNTAX VALIDATION")

    root = Path.cwd()

    # Find all Python files (excluding venv, node_modules, etc.)
    python_files = []
    for pattern in ['lambda/**/*.py', 'lambda_api/**/*.py', 'infra/**/*.py', 'tests/**/*.py']:
        python_files.extend(root.glob(pattern))

    syntax_errors = []

    for py_file in python_files:
        try:
            with open(py_file, 'r') as f:
                compile(f.read(), str(py_file), 'exec')
        except SyntaxError as e:
            syntax_errors.append((py_file, str(e)))

    if syntax_errors:
        print_check("Python syntax", False, f"Found {len(syntax_errors)} files with syntax errors")
        for file_path, error in syntax_errors[:5]:  # Show first 5
            print(f"  - {file_path}: {error}")
    else:
        print_check("Python syntax", True, f"All {len(python_files)} Python files have valid syntax")


def print_summary():
    """Print final summary."""
    print_header("VALIDATION SUMMARY")

    total_checks = checks_passed + checks_failed

    print(f"Total checks run: {BOLD}{total_checks}{RESET}")
    print(f"Passed: {GREEN}{checks_passed}{RESET}")
    print(f"Failed: {RED}{checks_failed}{RESET}")
    print(f"Warnings: {YELLOW}{checks_warned}{RESET}\n")

    if checks_failed == 0:
        print(f"{GREEN}{BOLD}✓ ALL CHECKS PASSED - READY FOR DEPLOYMENT{RESET}\n")
        print("Next steps:")
        print("  1. Configure AWS credentials: aws configure")
        print("  2. Bootstrap CDK (first time): cdk bootstrap")
        print("  3. Store Anthropic API key in Secrets Manager")
        print("  4. Deploy backend: cdk deploy --all")
        print("  5. Deploy frontend: See DEPLOYMENT_READINESS.md")
        print()
        return 0
    else:
        print(f"{RED}{BOLD}✗ {checks_failed} CHECK(S) FAILED{RESET}\n")
        print("Please fix the issues above before deploying.")
        print("See DEPLOYMENT_READINESS.md for detailed deployment instructions.")
        print()
        return 1


def main():
    """Run all validation checks."""
    print(f"\n{BOLD}Morning Reflection - Deployment Validation{RESET}")
    print("=" * 80)

    # Run all validation checks
    validate_project_structure()
    validate_lambda_code()
    validate_api_code()
    validate_frontend()
    validate_infrastructure()
    validate_configuration()
    validate_tests()
    validate_documentation()
    validate_dependencies()
    validate_cicd()
    validate_python_syntax()
    validate_cdk_synth()  # This one is optional (requires CDK CLI)

    # Print summary and exit
    exit_code = print_summary()
    sys.exit(exit_code)


if __name__ == '__main__':
    main()
