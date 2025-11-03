# Local Development Guide

This guide explains how to set up and run the Morning Reflection application locally for development and testing without deploying to AWS.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Backend Local Development](#backend-local-development)
3. [Frontend Local Development](#frontend-local-development)
4. [Testing](#testing)
5. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Required Software

1. **Python 3.12+**
   ```bash
   python --version  # Should be 3.12+
   ```

2. **Node.js 20+**
   ```bash
   node --version  # Should be 20+
   npm --version
   ```

3. **Git**
   ```bash
   git --version
   ```

### Optional (for advanced local testing)

4. **Docker** (for DynamoDB Local)
   ```bash
   docker --version
   ```

5. **AWS CLI** (for mocking AWS services)
   ```bash
   aws --version
   ```

---

## Backend Local Development

### 1. Install Python Dependencies

```bash
# Create virtual environment (recommended)
python -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows:
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install development dependencies
pip install pytest pytest-cov black flake8 mypy
```

### 2. Run Unit Tests

The backend tests use mocks for all AWS services, so they run locally without any AWS configuration:

```bash
# Run all backend tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=lambda --cov=lambda_api --cov-report=html

# Run specific test file
pytest tests/test_handler.py -v

# Run tests matching pattern
pytest tests/ -k "test_security" -v

# View coverage report
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
start htmlcov\index.html  # Windows
```

### 3. Manual Function Testing

You can test Lambda functions manually without deploying:

```bash
# Test quote loader
python -c "
import sys
sys.path.insert(0, 'lambda')
from quote_loader import QuoteLoader
from datetime import datetime

loader = QuoteLoader(bucket_name=None)  # None = load from local file
quote = loader.get_quote_for_date(datetime.now())
print(f'Quote: {quote[\"quote\"]}')
print(f'Attribution: {quote[\"attribution\"]}')
"

# Test security validator
python -c "
import sys
sys.path.insert(0, 'lambda_api')
from security import SecurityValidator

validator = SecurityValidator(config_path='config/security_config.json')
is_safe, sanitized, results = validator.validate_and_sanitize(
    'This is a test reflection about Stoic philosophy.'
)
print(f'Safe: {is_safe}')
print(f'Sanitized: {sanitized}')
"
```

### 4. Local DynamoDB (Optional)

For more realistic testing, you can run DynamoDB Local:

```bash
# Download and run DynamoDB Local with Docker
docker run -p 8000:8000 amazon/dynamodb-local

# In another terminal, create test tables
aws dynamodb create-table \
  --table-name Users \
  --attribute-definitions \
    AttributeName=user_id,AttributeType=S \
    AttributeName=email,AttributeType=S \
  --key-schema \
    AttributeName=user_id,KeyType=HASH \
  --global-secondary-indexes \
    "IndexName=EmailIndex,KeySchema=[{AttributeName=email,KeyType=HASH}],Projection={ProjectionType=ALL},ProvisionedThroughput={ReadCapacityUnits=5,WriteCapacityUnits=5}" \
  --provisioned-throughput \
    ReadCapacityUnits=5,WriteCapacityUnits=5 \
  --endpoint-url http://localhost:8000

# List tables
aws dynamodb list-tables --endpoint-url http://localhost:8000
```

### 5. Mock Anthropic API (For Testing)

For local testing without making real API calls:

```python
# tests/conftest.py already includes fixtures for this
# Example:
from unittest.mock import patch, MagicMock

@patch('anthropic_client.Anthropic')
def test_local(mock_anthropic):
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text="Test reflection")]
    mock_client.messages.create.return_value = mock_response
    mock_anthropic.return_value = mock_client

    # Your test code here
    result = generate_reflection(...)
    assert result == "Test reflection"
```

---

## Frontend Local Development

### 1. Install Dependencies

```bash
cd frontend
npm install
```

### 2. Configure Environment Variables

Create `.env` file for local development:

```bash
cd frontend
cat > .env << EOF
# Local development configuration
VITE_AWS_REGION=us-west-2
VITE_USER_POOL_ID=local-test-pool
VITE_USER_POOL_CLIENT_ID=local-test-client
VITE_API_URL=http://localhost:3000/api
VITE_APP_NAME=Morning Reflection (Local)
VITE_APP_URL=http://localhost:5173
EOF
```

### 3. Run Development Server

```bash
cd frontend
npm run dev
```

This starts Vite dev server at `http://localhost:5173` with:
- Hot module replacement (HMR)
- TypeScript type checking
- Fast refresh

### 4. Build for Production (Local)

```bash
cd frontend
npm run build

# Preview production build
npm run preview
```

### 5. Type Checking

```bash
cd frontend

# Run TypeScript type checker
npm run build  # Includes type checking

# Or use tsc directly
npx tsc --noEmit
```

### 6. Linting

```bash
cd frontend

# Run ESLint
npm run lint

# Fix auto-fixable issues
npm run lint -- --fix
```

---

## Testing

### Backend Tests

```bash
# Run all backend unit tests
pytest tests/ -v

# Run with markers
pytest tests/ -m unit -v  # Only unit tests
pytest tests/ -m security -v  # Only security tests

# Run specific test class
pytest tests/test_handler.py::TestHandlerFunction -v

# Run with coverage and HTML report
pytest tests/ --cov=lambda --cov=lambda_api --cov-report=html
open htmlcov/index.html
```

### Frontend Tests (E2E with Playwright)

```bash
cd frontend

# Install Playwright browsers (first time only)
npx playwright install

# Run E2E tests
npm run test:e2e

# Run in headed mode (see browser)
npx playwright test --headed

# Run specific test file
npx playwright test tests/e2e/login.spec.ts

# Debug mode (step through tests)
npx playwright test --debug
```

### Integration Testing (Backend + Frontend)

For full integration testing, you'll need to:

1. Deploy backend to AWS (or use mocks)
2. Configure frontend `.env` with real API endpoints
3. Run E2E tests against deployed environment

```bash
# Run E2E tests against staging
cd frontend
cat > .env.test << EOF
VITE_API_URL=https://staging-api.morningreflection.com
VITE_USER_POOL_ID=us-west-2_STAGING
VITE_USER_POOL_CLIENT_ID=staging-client-id
EOF

npm run test:e2e
```

---

## Development Workflow

### Recommended Workflow

1. **Start with tests** (TDD approach)
   ```bash
   # Write failing test
   pytest tests/test_new_feature.py -v  # Should fail
   ```

2. **Implement feature**
   ```bash
   # Write code in lambda/ or lambda_api/
   ```

3. **Run tests**
   ```bash
   pytest tests/test_new_feature.py -v  # Should pass
   ```

4. **Check code quality**
   ```bash
   # Format code
   black lambda/ lambda_api/ infra/ tests/

   # Lint code
   flake8 lambda/ lambda_api/ infra/ --max-line-length=120

   # Type check
   mypy lambda/ lambda_api/
   ```

5. **Run all tests**
   ```bash
   pytest tests/ --cov=lambda --cov=lambda_api
   ```

6. **Test frontend integration**
   ```bash
   cd frontend
   npm run dev
   # Manually test in browser
   ```

7. **Commit changes**
   ```bash
   git add .
   git commit -m "feat: Add new feature"
   git push
   ```

### Pre-commit Checks

Before committing, run:

```bash
# Validate deployment readiness
python scripts/validate_deployment.py

# Run all tests
pytest tests/ -v

# Check code formatting
black --check lambda/ lambda_api/ infra/ tests/

# Lint code
flake8 lambda/ lambda_api/ infra/ --max-line-length=120
```

Or set up pre-commit hooks (optional):

```bash
# Install pre-commit
pip install pre-commit

# Create .pre-commit-config.yaml
cat > .pre-commit-config.yaml << EOF
repos:
  - repo: https://github.com/psf/black
    rev: 23.7.0
    hooks:
      - id: black
        language_version: python3.12

  - repo: https://github.com/PyCQA/flake8
    rev: 6.1.0
    hooks:
      - id: flake8
        args: [--max-line-length=120, --extend-ignore=E203,W503]

  - repo: local
    hooks:
      - id: pytest
        name: pytest
        entry: pytest
        language: system
        pass_filenames: false
        always_run: true
        args: [tests/, -v]
EOF

# Install hooks
pre-commit install

# Now tests run automatically before each commit
```

---

## Troubleshooting

### Import Errors

**Problem**: `ModuleNotFoundError: No module named 'handler'`

**Solution**:
```bash
# Ensure you're running from project root
cd /path/to/morningreflection

# Verify Python path
python -c "import sys; print('\n'.join(sys.path))"

# Tests should work from project root
pytest tests/ -v
```

### AWS Service Errors (Even in Local Tests)

**Problem**: `botocore.exceptions.NoCredentialsError`

**Solution**: Tests should mock all AWS services. If you see this error, the test is missing a mock.

```python
# Add this decorator to your test
@patch('your_module.boto3.client')
def test_your_function(mock_boto3_client):
    mock_service = MagicMock()
    mock_boto3_client.return_value = mock_service
    # ... rest of test
```

### Frontend CORS Errors

**Problem**: `Access-Control-Allow-Origin header missing`

**Solution**: When running frontend locally with real backend:

1. Update API Gateway to allow `http://localhost:5173` origin, OR
2. Use a proxy in `vite.config.ts`:

```typescript
// frontend/vite.config.ts
export default defineConfig({
  server: {
    proxy: {
      '/api': {
        target: 'https://your-api.execute-api.us-west-2.amazonaws.com',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, '/prod')
      }
    }
  }
})
```

### Cognito Authentication Issues

**Problem**: Can't test login flow locally

**Solution**: Use Cognito test users:

```bash
# Create test user in your Cognito User Pool
aws cognito-idp admin-create-user \
  --user-pool-id us-west-2_YOUR_POOL_ID \
  --username test@example.com \
  --user-attributes Name=email,Value=test@example.com \
  --temporary-password TestPass123!

# Or use mock authentication in tests
# See frontend/tests/e2e/*.spec.ts for examples
```

### DynamoDB Local Connection Issues

**Problem**: Can't connect to DynamoDB Local

**Solution**:
```bash
# Check if Docker container is running
docker ps | grep dynamodb

# Verify endpoint is accessible
curl http://localhost:8000

# Use correct endpoint in code
import boto3
dynamodb = boto3.resource('dynamodb', endpoint_url='http://localhost:8000')
```

### Test Failures After Code Changes

**Problem**: Tests fail after refactoring

**Solution**:
```bash
# Run specific failing test with verbose output
pytest tests/test_handler.py::test_specific -vv

# Check what changed
git diff

# Update mocks if interfaces changed
# Update assertions if behavior changed
```

---

## Performance Tips

### Speed Up Tests

```bash
# Run tests in parallel (requires pytest-xdist)
pip install pytest-xdist
pytest tests/ -n auto -v

# Skip slow tests during development
pytest tests/ -m "not slow" -v

# Run only failed tests from last run
pytest tests/ --lf -v
```

### Speed Up Frontend Dev Server

```bash
cd frontend

# Use SWC instead of Babel (faster)
# Already configured in vite.config.ts

# Disable type checking during dev (re-enable for production)
# Already configured to run type checking in build only
```

### Reduce Test Execution Time

- Mock external services (Anthropic API, AWS services)
- Use fixtures to share setup between tests
- Run only relevant tests during development
- Use parallel test execution for CI/CD

---

## Next Steps

After setting up local development:

1. **Explore the codebase**: Read code in `lambda/`, `lambda_api/`, and `frontend/src/`
2. **Run tests**: Verify everything works locally
3. **Make changes**: Follow TDD workflow
4. **Deploy to AWS**: See `DEPLOYMENT_READINESS.md`

---

## Additional Resources

- **Testing Documentation**: See `tests/README.md` (if exists)
- **API Documentation**: See `Documentation/API_SPECIFICATION.md` (TODO)
- **Architecture**: See `ARCHITECTURE.md`
- **Deployment**: See `DEPLOYMENT_READINESS.md`

---

## Questions?

- Review `Documentation/` folder for detailed guides
- Check CloudWatch logs for errors (after deployment)
- See `README.md` for project overview
