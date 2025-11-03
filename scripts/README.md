# Scripts Directory

This directory contains utility scripts for deployment validation, local development, and maintenance.

## Available Scripts

### `validate_deployment.py`

**Purpose**: Pre-deployment validation script that verifies all code, configuration, and dependencies are ready for AWS deployment.

**Usage**:
```bash
python scripts/validate_deployment.py
```

**What it checks**:
- ✅ Project structure (directories and files)
- ✅ Lambda function code
- ✅ API handler code
- ✅ Frontend application
- ✅ CDK infrastructure code
- ✅ Configuration files (quotes database, security config)
- ✅ Test suite (pytest)
- ✅ Documentation
- ✅ Python dependencies
- ✅ CI/CD workflows
- ✅ Python syntax validation
- ✅ CDK synthesis (optional, requires CDK CLI)

**Exit codes**:
- `0` - All checks passed, ready for deployment
- `1` - One or more checks failed

**When to run**:
- Before first deployment
- After making infrastructure changes
- Before pushing to main branch (CI/CD)
- When troubleshooting deployment issues

**Example output**:
```
Morning Reflection - Deployment Validation
================================================================================

================================================================================
                               PROJECT STRUCTURE
================================================================================

✓ Lambda functions directory: lambda/
✓ API handlers directory: lambda_api/
✓ Frontend application directory: frontend/
...

================================================================================
                               VALIDATION SUMMARY
================================================================================

Total checks run: 72
Passed: 72
Failed: 0
Warnings: 1

✓ ALL CHECKS PASSED - READY FOR DEPLOYMENT
```

## Future Scripts (TODO)

### `local_dev_setup.sh`
Set up local development environment with DynamoDB Local and mock AWS services.

### `run_tests.sh`
Run all tests (backend + frontend + E2E) with coverage reports.

### `generate_docs.sh`
Generate API documentation from code comments.

### `cost_estimator.py`
Estimate monthly AWS costs based on expected usage.

### `backup_dynamodb.sh`
Backup DynamoDB tables to S3.

### `restore_dynamodb.sh`
Restore DynamoDB tables from S3 backup.

## Adding New Scripts

When adding new scripts to this directory:

1. **Make them executable**: `chmod +x scripts/your_script.sh`
2. **Add shebang**: Start with `#!/usr/bin/env python3` or `#!/bin/bash`
3. **Document here**: Add description to this README
4. **Add help text**: Support `--help` flag
5. **Exit codes**: Use 0 for success, non-zero for failure
6. **Error handling**: Catch exceptions and print meaningful errors
7. **Dry-run mode**: For destructive operations, support `--dry-run`

## Script Guidelines

### Python Scripts
- Use Python 3.9+
- Add type hints where appropriate
- Use argparse for command-line arguments
- Follow PEP 8 style guide
- Include docstrings

### Bash Scripts
- Use `set -euo pipefail` for safety
- Quote all variables
- Check for required commands before using
- Provide colored output for readability

### Error Messages
- Be specific about what went wrong
- Suggest how to fix the problem
- Include relevant file paths and line numbers

### Output Formatting
- Use colors for readability (green=success, red=error, yellow=warning)
- Show progress for long-running operations
- Provide summary at the end

## Dependencies

Scripts in this directory may require:
- Python 3.9+
- AWS CLI (for deployment scripts)
- CDK CLI (for infrastructure scripts)
- Node.js (for frontend scripts)
- Docker (for local development)

Check individual script documentation for specific requirements.
