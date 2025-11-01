# Phase 5: Deployment & Monitoring - Complete Guide

## Overview

Phase 5 implements comprehensive deployment automation, monitoring, and CI/CD pipelines for Morning Reflection. This phase makes the application production-ready with automated deployments, real-time monitoring, alerting, and end-to-end testing.

**Status**: Phase 5 Complete ✅

## What Was Implemented

### 1. AWS Amplify Hosting (CDK Integration)

**File**: `infra/stoic_stack.py` (lines 505-579)

Automated frontend hosting integrated directly into the CDK stack:

**Features**:
- Git-based continuous deployment
- Automatic environment variable injection from CDK outputs
- Build configuration for Vite + React
- Optional custom domain support
- Auto-deletion of feature branches

**Configuration**:
```python
# In cdk.json context, add:
{
  "github_token": "ghp_...",        # GitHub personal access token
  "github_repo": "owner/repo",      # Your repository
  "github_branch": "main",          # Branch to deploy
  "custom_domain": "app.morningreflection.com"  # Optional
}
```

**How It Works**:
1. CDK creates Amplify app connected to your GitHub repo
2. Amplify auto-detects Vite build configuration
3. Environment variables (User Pool ID, API URL) injected automatically
4. Every push to main branch triggers automatic deployment
5. Amplify provides a default domain (e.g., `main.d123abc.amplifyapp.com`)

### 2. CloudWatch Dashboard

**File**: `infra/stoic_stack.py` (lines 581-671)

Comprehensive monitoring dashboard showing all system metrics:

**Dashboard Widgets**:
1. **Daily Lambda Metrics**:
   - Invocations (5-min intervals)
   - Errors (5-min intervals)
   - Duration (avg + max)

2. **API Gateway Metrics**:
   - Total requests
   - Client errors (4xx)
   - Server errors (5xx)
   - Latency (avg + p99)

3. **DynamoDB Metrics** (3 tables):
   - Users table capacity (read/write units)
   - Reflections table capacity
   - Journal table capacity

4. **Cognito Metrics**:
   - User authentication activity

**Access**:
```
https://console.aws.amazon.com/cloudwatch/home?region=us-west-2#dashboards:name=MorningReflection-Metrics
```
(URL outputted after CDK deployment)

### 3. CloudWatch Alarms

**File**: `infra/stoic_stack.py` (lines 673-740)

Automated alerting for critical issues:

**Alarms Configured**:

| Alarm | Threshold | Action |
|-------|-----------|--------|
| Daily Lambda Errors | ≥1 error in 5 min | SNS notification |
| Daily Lambda Throttles | ≥1 throttle in 5 min | SNS notification |
| API Gateway 5xx Errors | ≥5 errors in 10 min | SNS notification |
| API Gateway High Latency | ≥2 seconds avg (15 min) | SNS notification |
| DynamoDB Throttles | ≥5 throttles in 10 min | SNS notification |

**SNS Topic**:
- Reuses existing security SNS topic from Phase 1
- Can add multiple email subscriptions
- Can integrate with PagerDuty, Slack, etc.

**To Subscribe**:
```bash
aws sns subscribe \
  --topic-arn arn:aws:sns:us-west-2:ACCOUNT:MorningReflection-SecurityAlerts \
  --protocol email \
  --notification-endpoint your-email@example.com
```

### 4. GitHub Actions CI/CD Pipeline

**Files**:
- `.github/workflows/ci.yml` - Continuous Integration
- `.github/workflows/deploy.yml` - Continuous Deployment
- `.github/workflows/e2e-tests.yml` - End-to-End Tests

#### CI Workflow (`ci.yml`)

**Triggers**: Pull requests and pushes to `main`/`develop`

**Jobs**:
1. **Backend Tests**:
   - Python linting (flake8, black)
   - Type checking (mypy)
   - Unit tests (pytest with coverage)
   - Upload coverage to Codecov

2. **Frontend Tests**:
   - TypeScript type checking
   - ESLint linting
   - Production build validation

3. **CDK Synth**:
   - Validates CDK stack can synthesize
   - Catches infrastructure-as-code errors early

**Configuration**:
No secrets required for CI - runs on all PRs automatically.

#### CD Workflow (`deploy.yml`)

**Triggers**: Push to `main` or manual workflow dispatch

**Jobs**:
1. **Deploy Backend** (CDK):
   - Bootstrap CDK (if needed)
   - Deploy stack with `--require-approval never`
   - Extract CloudFormation outputs
   - Pass outputs to frontend job

2. **Deploy Frontend** (Amplify):
   - Build frontend with CDK outputs as env vars
   - Trigger Amplify deployment
   - Monitor deployment status

3. **Notify Deployment**:
   - Send success/failure notification
   - Can integrate with Slack, Teams, etc.

**Required Secrets** (in GitHub repository settings):
```
AWS_ROLE_ARN         # IAM role ARN for OIDC authentication
AWS_REGION           # AWS region (default: us-west-2)
AWS_ACCOUNT_ID       # Your AWS account ID
```

**OIDC Authentication**:
Uses GitHub Actions OIDC instead of long-lived access keys (more secure).

To set up:
```bash
# Create OIDC provider (one-time setup)
aws iam create-open-id-connect-provider \
  --url https://token.actions.githubusercontent.com \
  --client-id-list sts.amazonaws.com

# Create trust policy for GitHub Actions
# (See AWS documentation for full policy)
```

#### E2E Tests Workflow (`e2e-tests.yml`)

**Triggers**: Pull requests to `main`, pushes to `main`, manual dispatch

**Job**: Run Playwright Tests
- Install Playwright browsers
- Build frontend
- Run all E2E tests
- Upload test reports and screenshots

**Required Secrets**:
```
TEST_USER_POOL_ID       # Cognito pool for testing
TEST_USER_POOL_CLIENT_ID
TEST_API_URL            # API Gateway URL for testing
TEST_USER_EMAIL         # Test user credentials
TEST_USER_PASSWORD
```

### 5. Playwright End-to-End Tests

**Files**:
- `frontend/playwright.config.ts` - Playwright configuration
- `frontend/tests/e2e/auth.spec.ts` - Authentication tests
- `frontend/tests/e2e/app.spec.ts` - Application tests
- `frontend/tests/e2e/helpers/auth.ts` - Test helpers

**Test Coverage**:

**Authentication Tests** (`auth.spec.ts`):
- ✓ Login page display
- ✓ Form validation (empty fields, invalid email)
- ✓ Navigation (signup, forgot password)
- ✓ Signup form display
- ✓ Password requirements validation
- ✓ Password confirmation matching
- ✓ Protected route redirects

**Application Tests** (`app.spec.ts`):
- ✓ Dashboard display
- ✓ Reflection content loading
- ✓ Journal entry creation
- ✓ Calendar display
- ✓ Calendar navigation
- ✓ Settings page
- ✓ Email preference toggles
- ✓ Account deletion flow
- ✓ Responsive design (mobile)

**Test Configuration**:
- Tests run against `localhost:4173` (Vite preview)
- Supports Chromium, Firefox, WebKit browsers
- Mobile viewports (Pixel 5, iPhone 12)
- Screenshots on failure
- Traces on retry

**Running Tests**:
```bash
cd frontend

# Install Playwright browsers (first time only)
npx playwright install

# Run all tests
npm run test:e2e

# Run with UI (interactive mode)
npm run test:e2e:ui

# Run in headed mode (see browser)
npm run test:e2e:headed
```

### 6. Deployment Automation Scripts

**Files**:
- `scripts/deploy-all.sh` - Complete deployment
- `scripts/check-deployment.sh` - Health check
- `scripts/destroy-all.sh` - Tear down infrastructure

#### Deploy All Script

**Purpose**: One-command full stack deployment

**What it does**:
1. Deploys backend via CDK
2. Extracts CDK outputs (User Pool ID, API URL, etc.)
3. Updates frontend `.env` with actual values
4. Builds frontend
5. Triggers Amplify deployment (if configured)
6. Displays summary with all URLs

**Usage**:
```bash
./scripts/deploy-all.sh
```

**Output**:
```
Backend Resources:
  - User Pool ID: us-west-2_ABC123
  - API URL: https://xyz123.execute-api.us-west-2.amazonaws.com/prod
  - Region: us-west-2

Frontend URL: https://main.d123abc.amplifyapp.com

CloudWatch Dashboard:
  https://console.aws.amazon.com/cloudwatch/...

All done! 🎉
```

#### Check Deployment Script

**Purpose**: Verify deployment health and status

**What it checks**:
- CloudFormation stack status
- Lambda function state and last update
- DynamoDB table status (all 3 tables)
- API Gateway accessibility (HTTP ping)
- Amplify deployment status
- Recent Lambda errors (last hour)

**Usage**:
```bash
./scripts/check-deployment.sh
```

**Output**:
```
✓ Stack Status: UPDATE_COMPLETE

Backend Resources:
User Pool ID: us-west-2_ABC123
API URL: https://xyz123...
Lambda Function: MorningReflectionStack-DailyLambda-XYZ

Lambda Status:
✓ Lambda: Active
Last Updated: 2025-01-15T10:30:00.000+0000

DynamoDB Tables:
✓ Users Table: ACTIVE
✓ Reflections Table: ACTIVE
✓ Journal Table: ACTIVE

API Gateway:
✓ API Gateway: Responding (403)

✓ No errors in last hour
```

#### Destroy All Script

**Purpose**: Complete infrastructure teardown

**Safety Features**:
- Requires typing "yes" to confirm
- Requires typing "DELETE EVERYTHING" to double-confirm
- Lists all resources that will be deleted
- Warns about data loss

**Usage**:
```bash
./scripts/destroy-all.sh
```

**Use Cases**:
- Cleaning up test/staging environments
- Cost management (delete when not in use)
- Starting fresh after major changes

## Deployment Guide

### Prerequisites

1. **AWS CLI installed and configured**:
   ```bash
   aws configure
   ```

2. **AWS CDK installed**:
   ```bash
   npm install -g aws-cdk
   ```

3. **Python dependencies installed**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Node.js dependencies installed** (frontend):
   ```bash
   cd frontend && npm install
   ```

5. **Anthropic API key in Secrets Manager**:
   ```bash
   ./scripts/setup-secrets.sh
   ```

### Method 1: Automated Deployment (Recommended)

**Single command deployment**:

```bash
./scripts/deploy-all.sh
```

This handles everything:
- Backend deployment
- Environment configuration
- Frontend build
- Amplify trigger
- Output display

### Method 2: Manual Deployment

**Step 1: Deploy Backend**
```bash
cdk deploy
```

**Step 2: Get Outputs**
```bash
aws cloudformation describe-stacks \
  --stack-name MorningReflectionStack \
  --query "Stacks[0].Outputs"
```

**Step 3: Configure Frontend**
```bash
cd frontend
cp .env.example .env
# Edit .env with CDK outputs
```

**Step 4: Build & Deploy Frontend**

**Option A: Amplify (automatic)**
- Push to GitHub main branch
- Amplify deploys automatically

**Option B: Manual S3 deployment**
```bash
npm run build
aws s3 sync dist/ s3://your-bucket/
```

**Option C: Vercel/Netlify**
```bash
npm run build
vercel --prod
# or
netlify deploy --prod --dir=dist
```

### Method 3: GitHub Actions (CI/CD)

**Setup**:
1. Add secrets to GitHub repository settings:
   - `AWS_ROLE_ARN`
   - `AWS_ACCOUNT_ID`
   - `AWS_REGION`

2. Push to `main` branch

3. GitHub Actions automatically:
   - Deploys backend
   - Builds frontend
   - Triggers Amplify

**Monitor**:
- Go to Actions tab in GitHub
- View deployment logs in real-time

## Configuration

### CDK Context (cdk.json)

**Required values**:
```json
{
  "sender_email": "reflections@morningreflection.com",
  "sender_domain": "morningreflection.com",
  "anthropic_api_key": "USE_SECRETS_MANAGER"
}
```

**Optional values for Amplify**:
```json
{
  "github_token": "ghp_...",
  "github_repo": "jamesmoon2/morningreflection",
  "github_branch": "main",
  "custom_domain": "app.morningreflection.com"
}
```

**Security note**: Add `github_token` to `.gitignore` or use environment variable:
```bash
cdk deploy --context github_token=$GITHUB_TOKEN
```

### Environment Variables (Frontend)

**Development** (`.env`):
```env
VITE_AWS_REGION=us-west-2
VITE_USER_POOL_ID=us-west-2_ABC123
VITE_USER_POOL_CLIENT_ID=xyz123
VITE_API_URL=http://localhost:3000
VITE_APP_NAME=Morning Reflection (Dev)
VITE_APP_URL=http://localhost:5173
```

**Production** (set by Amplify or deploy script):
```env
VITE_AWS_REGION=us-west-2
VITE_USER_POOL_ID=${CDK_OUTPUT_USER_POOL_ID}
VITE_USER_POOL_CLIENT_ID=${CDK_OUTPUT_CLIENT_ID}
VITE_API_URL=${CDK_OUTPUT_API_URL}
VITE_APP_NAME=Morning Reflection
VITE_APP_URL=https://app.morningreflection.com
```

## Monitoring & Alerts

### CloudWatch Dashboard

**Access**:
1. Go to AWS Console → CloudWatch → Dashboards
2. Select "MorningReflection-Metrics"
3. Or use the URL from deployment output

**Key Metrics to Watch**:
- **Lambda Errors**: Should be 0
- **API Latency**: Should be <500ms average
- **DynamoDB Capacity**: Should stay well below limits
- **Cognito Activity**: Track user growth

### CloudWatch Alarms

**View Alarms**:
```bash
aws cloudwatch describe-alarms \
  --alarm-name-prefix "MorningReflection"
```

**Subscribe to Alerts**:
```bash
# Get SNS topic ARN from CDK output
SNS_ARN=$(aws cloudformation describe-stacks \
  --stack-name MorningReflectionStack \
  --query "Stacks[0].Outputs[?OutputKey=='SecurityAlertTopicArn'].OutputValue" \
  --output text)

# Subscribe email
aws sns subscribe \
  --topic-arn "$SNS_ARN" \
  --protocol email \
  --notification-endpoint your-email@example.com

# Confirm subscription via email
```

**Alarm States**:
- **OK**: Everything normal (green)
- **INSUFFICIENT_DATA**: Not enough data yet (gray)
- **ALARM**: Threshold breached (red)

### CloudWatch Logs

**View Lambda Logs**:
```bash
# Get log group name
LOG_GROUP="/aws/lambda/MorningReflectionStack-DailyLambda-..."

# Tail logs in real-time
aws logs tail "$LOG_GROUP" --follow

# Search for errors
aws logs filter-log-events \
  --log-group-name "$LOG_GROUP" \
  --filter-pattern "ERROR"
```

**View API Gateway Logs**:
```bash
aws logs tail "/aws/apigateway/MorningReflection-API" --follow
```

## Testing

### Unit Tests (Backend)

```bash
pytest tests/ --cov=lambda --cov=lambda_api
```

### E2E Tests (Frontend)

```bash
cd frontend
npm run test:e2e
```

**Test Reports**:
- Located in `frontend/playwright-report/`
- Open `index.html` in browser to view

**CI/CD Integration**:
- E2E tests run automatically on PRs
- Test reports uploaded as GitHub Actions artifacts
- Failures block merge

### Manual Testing Checklist

**Authentication**:
- [ ] Sign up new user
- [ ] Verify email
- [ ] Sign in
- [ ] Sign out
- [ ] Request password reset
- [ ] Reset password with code

**Dashboard**:
- [ ] View today's reflection
- [ ] See journaling prompt
- [ ] Write journal entry
- [ ] Save journal
- [ ] Word count updates
- [ ] Navigate to calendar

**Calendar**:
- [ ] View current month
- [ ] Navigate to previous month
- [ ] Navigate to next month
- [ ] Click on a date with reflection
- [ ] Click on a date with journal entry
- [ ] See visual indicators (dots)

**Daily Reflection Page**:
- [ ] View reflection for specific date
- [ ] View journal entry if exists
- [ ] Edit journal entry
- [ ] Save changes
- [ ] Magic link from email works

**Settings**:
- [ ] View account info
- [ ] Toggle email preference
- [ ] Change delivery time
- [ ] Change timezone
- [ ] Save settings
- [ ] Delete account (confirmation works)

**Mobile Responsiveness**:
- [ ] All pages work on mobile (< 768px)
- [ ] Navigation menu collapses
- [ ] Forms are usable
- [ ] Calendar is readable

## Troubleshooting

### Common Issues

**Issue**: CDK deployment fails with "Stack already exists"
**Solution**:
```bash
cdk diff  # Check what changed
cdk deploy  # Try again
```

**Issue**: Amplify build fails
**Solution**:
1. Check Amplify console for build logs
2. Verify environment variables are set
3. Test build locally: `cd frontend && npm run build`

**Issue**: API returns 403 for all requests
**Solution**:
- This is normal! API requires authentication
- Test with authenticated request:
  ```bash
  # Get token from Cognito
  TOKEN="..."
  curl -H "Authorization: Bearer $TOKEN" $API_URL/user/profile
  ```

**Issue**: Frontend can't connect to API
**Solution**:
1. Check `VITE_API_URL` in `.env`
2. Verify API Gateway is deployed
3. Check CORS configuration
4. Check browser console for errors

**Issue**: Lambda function timing out
**Solution**:
1. Check CloudWatch logs for errors
2. Verify Anthropic API key is set in Secrets Manager
3. Increase Lambda timeout in CDK:
   ```python
   timeout=Duration.minutes(5)
   ```

**Issue**: DynamoDB throttling
**Solution**:
1. Check CloudWatch metrics
2. Consider switching to provisioned capacity
3. Add auto-scaling

**Issue**: GitHub Actions deployment fails with permission errors
**Solution**:
1. Verify OIDC provider is set up
2. Check IAM role trust policy
3. Verify role has necessary permissions (CloudFormation, Lambda, DynamoDB, etc.)

### Getting Help

**View Stack Events**:
```bash
aws cloudformation describe-stack-events \
  --stack-name MorningReflectionStack \
  --max-items 20
```

**Check Lambda Last Error**:
```bash
aws lambda get-function \
  --function-name MorningReflectionStack-DailyLambda-... \
  --query "Configuration.LastUpdateStatus"
```

**View Recent Logs**:
```bash
./scripts/check-deployment.sh
```

## Cost Breakdown

### Phase 5 Additional Costs

| Service | Usage | Cost/Month |
|---------|-------|------------|
| CloudWatch Dashboards | 1 dashboard, 12 widgets | $3.00 |
| CloudWatch Alarms | 5 alarms | $0.50 |
| CloudWatch Logs | ~1 GB/month | $0.50 |
| Amplify Hosting | 1000 users, 1GB transfer | $0.50 |
| **Phase 5 Total** | | **$4.50** |

### Total Project Cost

| Phase | Cost/Month |
|-------|------------|
| Phases 1-3 (Backend) | $10.50 |
| Phase 4 (Frontend) | $0.50 |
| Phase 5 (Monitoring + Amplify) | $4.50 |
| **Total** | **$15.50** |

**Still 22.5% under $20 budget!** 🎉

## Security Considerations

### OIDC Authentication (GitHub Actions)

**Why OIDC > Access Keys**:
- No long-lived credentials in GitHub
- Tokens expire after use
- Scoped to specific repository
- Can't be leaked in logs

**Setup**:
```bash
# Create OIDC provider (one-time)
aws iam create-open-id-connect-provider \
  --url https://token.actions.githubusercontent.com \
  --client-id-list sts.amazonaws.com \
  --thumbprint-list 6938fd4d98bab03faadb97b34396831e3780aea1

# Create role with trust policy allowing GitHub Actions
# (See AWS documentation for full policy)
```

### Secrets Management

**Never commit**:
- GitHub tokens
- AWS access keys
- Anthropic API keys
- User passwords

**Use**:
- AWS Secrets Manager for API keys
- GitHub Secrets for CI/CD credentials
- Environment variables for configuration

### CloudWatch Logs

**Log Retention**:
- Default: Never expire
- Recommended: 30-90 days
- To set:
  ```python
  logs.RetentionDays.ONE_MONTH
  ```

**Sensitive Data**:
- Never log passwords
- Never log API keys
- Redact PII in logs

## Next Steps

### Phase 6: Testing & Security Audit (Next Phase)

1. **Comprehensive E2E Testing**:
   - Add authenticated test scenarios
   - Test all user flows end-to-end
   - Add performance tests

2. **Security Audit**:
   - OWASP Top 10 testing
   - Penetration testing
   - Dependency vulnerability scan

3. **Load Testing**:
   - Test with 100+ concurrent users
   - Verify auto-scaling works
   - Identify bottlenecks

4. **Accessibility Audit**:
   - WCAG 2.1 AA compliance
   - Screen reader testing
   - Keyboard navigation testing

### Phase 7: Production Launch

1. **Beta Testing**:
   - Invite 10-20 beta users
   - Gather feedback
   - Fix bugs

2. **Documentation**:
   - User guide
   - API documentation
   - Admin guide

3. **Production Hardening**:
   - Enable AWS GuardDuty
   - Set up AWS WAF
   - Configure backup/recovery

4. **Marketing**:
   - Landing page
   - Social media presence
   - Email campaigns

---

**Phase 5 Status**: ✅ Complete

**Deployment Ready**: YES

**Monitoring Ready**: YES

**CI/CD Ready**: YES

**Next Phase**: Phase 6 - Testing & Security Audit
