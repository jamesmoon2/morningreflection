# Phase 2 Setup Guide: Backend - Auth & Database

**Status**: Phase 2 Complete ✅
**Date Completed**: November 1, 2024
**Prerequisites**: Phase 1 completed
**Next Phase**: Phase 3 - Reflections & Journaling Enhancement

---

## Overview

Phase 2 implements the backend infrastructure for user authentication, database storage, and API endpoints. This includes:

- Amazon Cognito User Pool with 2FA support
- DynamoDB tables for users, reflections, and journal entries
- API Gateway with Cognito authorizer
- Lambda functions for API handlers

### What Was Built

1. ✅ Cognito User Pool with enterprise-grade security
2. ✅ Three DynamoDB tables (Users, Reflections, JournalEntries)
3. ✅ REST API with 12 endpoints
4. ✅ Lambda functions for user management, reflections, and journaling
5. ✅ Security validation for journal entries

---

## Architecture Components

### Cognito User Pool

**Configuration**:
- User pool name: `MorningReflection-Users`
- Sign-in: Email only (no username)
- Email verification: Automatic
- Password policy: 12+ chars, uppercase, lowercase, digits, symbols
- MFA: Optional (TOTP + SMS)
- Advanced security: Compromised credentials check enabled

**User Pool Client**:
- Client name: `MorningReflection-WebApp`
- Client type: Public (no secret for SPA)
- Auth flows: USER_PASSWORD, USER_SRP
- Token validity: Access/ID 1 hour, Refresh 30 days

### DynamoDB Tables

#### Table 1: MorningReflection-Users

| Attribute | Type | Key | Description |
|-----------|------|-----|-------------|
| user_id | String | PK | Cognito sub (user ID) |
| email | String | GSI | User email address |
| email_verified | Boolean | | Verification status |
| created_at | String | | ISO 8601 timestamp |
| preferences | Map | | User preferences object |
| subscription_status | String | | active, paused, cancelled |
| timezone | String | | e.g., America/Los_Angeles |
| delivery_time | String | | e.g., 06:00 |
| last_login | String | | ISO 8601 timestamp |

**GSI**: `Email-index` on `email` field

---

#### Table 2: MorningReflection-Reflections

| Attribute | Type | Key | Description |
|-----------|------|-----|-------------|
| date | String | PK | YYYY-MM-DD format |
| quote | String | | Stoic quote |
| attribution | String | | Quote author |
| theme | String | | Monthly theme |
| reflection | String | | Generated reflection (250-450 words) |
| journaling_prompt | String | | Generated prompt (Phase 3) |
| generated_at | String | | ISO 8601 timestamp |
| model_version | String | | Claude model used |
| security_report | Map | | Security validation results |

---

#### Table 3: MorningReflection-JournalEntries

| Attribute | Type | Key | Description |
|-----------|------|-----|-------------|
| user_id | String | PK | Cognito sub (user ID) |
| date | String | SK | YYYY-MM-DD format |
| entry | String | | Journal text (max 10K chars) |
| word_count | Number | | Entry word count |
| created_at | String | | ISO 8601 timestamp |
| updated_at | String | | ISO 8601 timestamp |

---

### API Gateway Endpoints

**Base URL**: `https://<api-id>.execute-api.us-west-2.amazonaws.com/prod`

All endpoints require Cognito JWT token in `Authorization` header.

#### User Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/user/profile` | Get user profile |
| PUT | `/user/profile` | Update user profile |
| PUT | `/user/preferences` | Update delivery preferences |
| DELETE | `/user/account` | Delete user account (GDPR) |

#### Reflection Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/reflections/today` | Get today's reflection |
| GET | `/reflections/{date}` | Get reflection for specific date |
| GET | `/reflections/calendar?month=YYYY-MM` | Get calendar metadata |

#### Journal Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/journal` | Create/update journal entry |
| GET | `/journal/{date}` | Get journal entry for date |
| DELETE | `/journal/{date}` | Delete journal entry |
| GET | `/journal/list?from=X&to=Y&limit=N` | List journal entries |

---

## Lambda Functions

### 1. MorningReflection-UserApi

**Handler**: `user_api.lambda_handler`
**Memory**: 256 MB
**Timeout**: 30 seconds

**Responsibilities**:
- User profile management
- Preferences updates
- Account deletion (GDPR compliance)
- Auto-creates DynamoDB user record on first API call

**Permissions**:
- DynamoDB: Read/write Users table
- DynamoDB: Read Reflections table
- Cognito: Admin delete user
- S3: Read bucket

---

### 2. MorningReflection-ReflectionsApi

**Handler**: `reflections_api.lambda_handler`
**Memory**: 256 MB
**Timeout**: 30 seconds

**Responsibilities**:
- Serve daily reflections
- Serve historical reflections
- Generate calendar metadata

**Permissions**:
- DynamoDB: Read Reflections table
- S3: Read bucket

---

### 3. MorningReflection-JournalApi

**Handler**: `journal_api.lambda_handler`
**Memory**: 512 MB (more for validation)
**Timeout**: 30 seconds

**Responsibilities**:
- Create/update journal entries
- Retrieve journal entries
- Delete journal entries
- List journal entries with filtering
- **Security validation** (XSS, scripts, malicious patterns)

**Permissions**:
- DynamoDB: Read/write JournalEntries table
- DynamoDB: Read Users table
- S3: Read bucket

---

## Security Features

### 1. Authentication (Cognito)

**Password Requirements**:
- Minimum 12 characters
- Uppercase + lowercase + digits + symbols
- No common passwords (compromised credentials check)

**MFA Options**:
- TOTP (Google Authenticator, Authy, 1Password)
- SMS backup

**Session Security**:
- Short-lived access tokens (1 hour)
- Refresh token rotation enabled
- Device tracking for trusted devices

### 2. Journal Entry Validation

**Security Checks** (reuses Phase 1 security modules):
- Content sanitization (remove control chars, normalize whitespace)
- Malicious pattern detection (XSS, scripts, event handlers)
- Character validation (homoglyphs, excessive repetition)
- Length limits (max 10,000 chars)

**Input/Output**:
- All user input sanitized before storage
- HTML-escaped output
- No URLs allowed (configurable)

### 3. API Security

**Authorization**:
- All endpoints require valid Cognito JWT
- JWT signature validation
- JWT expiration check
- User ID extraction from token claims

**Rate Limiting**:
- 100 requests/second per API
- 200 burst capacity

**CORS**:
- Configured for cross-origin requests
- Update `allow_origins` in production

---

## Deployment Steps

### Prerequisites

1. **Phase 1 Completed**:
   - Secrets Manager secret created
   - SES domain verified
   - CDK stack deployed

2. **AWS CLI Configured**:
   ```bash
   aws sts get-caller-identity
   ```

---

### Step 1: Deploy Updated CDK Stack

```bash
cd /home/user/morningreflection

# Synthesize to review changes
cdk synth

# Deploy
cdk deploy
```

**What This Creates**:
- Cognito User Pool + Client
- 3 DynamoDB tables
- API Gateway REST API
- 3 Lambda functions (UserApi, ReflectionsApi, JournalApi)
- IAM roles and permissions

**Expected Output**:
```
Outputs:
StoicStack.ApiUrl = https://abc123xyz.execute-api.us-west-2.amazonaws.com/prod/
StoicStack.UserPoolId = us-west-2_ABC123XYZ
StoicStack.UserPoolClientId = 1a2b3c4d5e6f7g8h9i0j
StoicStack.UsersTableName = MorningReflection-Users
StoicStack.ReflectionsTableName = MorningReflection-Reflections
StoicStack.JournalTableName = MorningReflection-JournalEntries
```

**Save these values** - you'll need them for the frontend (Phase 4).

---

### Step 2: Verify Cognito User Pool

```bash
# Get User Pool ID from CDK outputs
USER_POOL_ID=$(aws cloudformation describe-stacks \
  --stack-name StoicStack \
  --region us-west-2 \
  --query 'Stacks[0].Outputs[?OutputKey==`UserPoolId`].OutputValue' \
  --output text)

echo "User Pool ID: $USER_POOL_ID"

# Describe User Pool
aws cognito-idp describe-user-pool \
  --user-pool-id $USER_POOL_ID \
  --region us-west-2
```

**Verify**:
- ✅ Password policy: 12+ chars, symbols required
- ✅ MFA: Optional
- ✅ Advanced security: Enabled
- ✅ Email verification: Enabled

---

### Step 3: Verify DynamoDB Tables

```bash
# List tables
aws dynamodb list-tables --region us-west-2 | grep MorningReflection

# Describe Users table
aws dynamodb describe-table \
  --table-name MorningReflection-Users \
  --region us-west-2

# Check encryption and PITR
aws dynamodb describe-continuous-backups \
  --table-name MorningReflection-Users \
  --region us-west-2
```

**Verify**:
- ✅ Encryption: AWS_MANAGED
- ✅ Point-in-time recovery: Enabled
- ✅ Billing mode: PAY_PER_REQUEST

Repeat for `MorningReflection-Reflections` and `MorningReflection-JournalEntries`.

---

### Step 4: Verify API Gateway

```bash
# Get API URL
API_URL=$(aws cloudformation describe-stacks \
  --stack-name StoicStack \
  --region us-west-2 \
  --query 'Stacks[0].Outputs[?OutputKey==`ApiUrl`].OutputValue' \
  --output text)

echo "API URL: $API_URL"

# Test OPTIONS (CORS preflight) - should work without auth
curl -X OPTIONS $API_URL/user/profile \
  -H "Origin: http://localhost:3000" \
  -v
```

**Expected**: `200 OK` with CORS headers.

---

### Step 5: Create Test User

```bash
# Get User Pool Client ID
CLIENT_ID=$(aws cloudformation describe-stacks \
  --stack-name StoicStack \
  --region us-west-2 \
  --query 'Stacks[0].Outputs[?OutputKey==`UserPoolClientId`].OutputValue' \
  --output text)

# Sign up a test user
aws cognito-idp sign-up \
  --client-id $CLIENT_ID \
  --username test@example.com \
  --password "TestPassword123!" \
  --user-attributes Name=email,Value=test@example.com \
  --region us-west-2

# Verify the user (admin command for testing)
aws cognito-idp admin-confirm-sign-up \
  --user-pool-id $USER_POOL_ID \
  --username test@example.com \
  --region us-west-2
```

---

### Step 6: Test Authentication Flow

```bash
# Authenticate user
AUTH_RESPONSE=$(aws cognito-idp initiate-auth \
  --auth-flow USER_PASSWORD_AUTH \
  --client-id $CLIENT_ID \
  --auth-parameters USERNAME=test@example.com,PASSWORD="TestPassword123!" \
  --region us-west-2)

# Extract ID token
ID_TOKEN=$(echo $AUTH_RESPONSE | jq -r '.AuthenticationResult.IdToken')

echo "ID Token: $ID_TOKEN"
```

---

### Step 7: Test API Endpoints

```bash
# Test GET /user/profile (should auto-create user in DynamoDB)
curl -X GET $API_URL/user/profile \
  -H "Authorization: Bearer $ID_TOKEN" \
  -H "Content-Type: application/json" | jq '.'

# Expected response:
# {
#   "user_id": "...",
#   "email": "test@example.com",
#   "subscription_status": "active",
#   "preferences": { ... }
# }
```

```bash
# Test PUT /user/preferences
curl -X PUT $API_URL/user/preferences \
  -H "Authorization: Bearer $ID_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "delivery_time": "07:00",
    "timezone": "America/New_York",
    "email_enabled": true
  }' | jq '.'
```

```bash
# Test GET /reflections/today (will be 404 until Phase 3)
curl -X GET $API_URL/reflections/today \
  -H "Authorization: Bearer $ID_TOKEN" \
  -H "Content-Type: application/json" | jq '.'

# Expected: 404 (no reflections in DB yet)
```

```bash
# Test POST /journal (create journal entry)
curl -X POST $API_URL/journal \
  -H "Authorization: Bearer $ID_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "date": "2024-11-01",
    "entry": "Today I practiced mindfulness and gratitude. It was a good day."
  }' | jq '.'

# Expected: 201 Created
```

```bash
# Test GET /journal/{date}
curl -X GET $API_URL/journal/2024-11-01 \
  -H "Authorization: Bearer $ID_TOKEN" \
  -H "Content-Type: application/json" | jq '.'
```

```bash
# Test GET /journal/list
curl -X GET "$API_URL/journal/list?limit=10" \
  -H "Authorization: Bearer $ID_TOKEN" \
  -H "Content-Type: application/json" | jq '.'
```

---

## What's Working Now

✅ **Authentication**:
- User signup with email verification
- Login with password
- JWT token generation
- Token-based API authorization

✅ **User Management**:
- Profile retrieval (auto-creates DynamoDB record)
- Preferences updates (delivery time, timezone, email settings)
- Account deletion (GDPR-compliant hard delete)

✅ **Journaling**:
- Create/update journal entries
- Retrieve journal entries by date
- Delete journal entries
- List journal entries with filtering
- Security validation (XSS, scripts, malicious patterns)

✅ **Reflections API** (ready for Phase 3):
- GET today's reflection (will return 404 until Phase 3)
- GET historical reflections
- GET calendar metadata

---

## What's NOT Working Yet

❌ **Reflections Generation**:
- No reflections in DynamoDB yet (Phase 3)
- Daily Lambda doesn't write to DynamoDB yet (Phase 3)
- Journaling prompts not generated yet (Phase 3)

❌ **Frontend**:
- No web application UI (Phase 4)
- No React app (Phase 4)
- Can only test via curl/Postman

❌ **2FA Setup**:
- 2FA endpoints not implemented (would need custom Cognito triggers or frontend flow)
- Users can enable 2FA through AWS Cognito SDK in frontend (Phase 4)

---

## Testing & Verification

### Unit Tests ✅ COMPLETE

Phase 2 Lambda functions now have comprehensive unit tests:

```bash
# Run all API endpoint tests
pytest tests/lambda_api/test_user_api.py -v
pytest tests/lambda_api/test_reflections_api.py -v
pytest tests/lambda_api/test_journal_api.py -v

# Run all backend tests
pytest tests/ -v

# Run with coverage
pytest --cov=lambda --cov=lambda_api --cov-report=html
```

**Test Coverage:**
- `tests/lambda_api/test_user_api.py` - 14+ tests for user API endpoints
- `tests/lambda_api/test_reflections_api.py` - 16+ tests for reflections API
- `tests/lambda_api/test_journal_api.py` - 25+ tests for journal API
- `tests/lambda_api/test_dynamodb_operations.py` - 15+ tests for DynamoDB CRUD
- `tests/lambda_api/test_api_utils.py` - 15+ tests for API utilities
- See pytest.ini for test organization and markers

### Integration Tests

Use the curl commands in Step 7 above, or use Postman:

**Postman Collection** (create manually):
1. Environment variables: `API_URL`, `ID_TOKEN`
2. GET /user/profile
3. PUT /user/preferences
4. POST /journal
5. GET /journal/{date}
6. DELETE /journal/{date}

---

## Troubleshooting

### Issue: "Unauthorized" (401)

**Cause**: JWT token is invalid or expired.

**Solution**:
```bash
# Re-authenticate
AUTH_RESPONSE=$(aws cognito-idp initiate-auth \
  --auth-flow USER_PASSWORD_AUTH \
  --client-id $CLIENT_ID \
  --auth-parameters USERNAME=test@example.com,PASSWORD="TestPassword123!" \
  --region us-west-2)

ID_TOKEN=$(echo $AUTH_RESPONSE | jq -r '.AuthenticationResult.IdToken')
```

---

### Issue: "User not confirmed"

**Cause**: User email not verified.

**Solution**:
```bash
# Admin confirm user (for testing)
aws cognito-idp admin-confirm-sign-up \
  --user-pool-id $USER_POOL_ID \
  --username test@example.com \
  --region us-west-2
```

---

### Issue: Lambda timeout or error

**Cause**: Lambda doesn't have required permissions or environment variables.

**Solution**:
```bash
# Check Lambda logs
aws logs tail /aws/lambda/MorningReflection-UserApi --follow

# Check Lambda environment variables
aws lambda get-function-configuration \
  --function-name MorningReflection-UserApi \
  --region us-west-2 \
  --query 'Environment.Variables'
```

---

### Issue: DynamoDB table not found

**Cause**: CDK deployment incomplete or table name mismatch.

**Solution**:
```bash
# List tables
aws dynamodb list-tables --region us-west-2

# Verify table names in CDK outputs
aws cloudformation describe-stacks \
  --stack-name StoicStack \
  --region us-west-2 \
  --query 'Stacks[0].Outputs'
```

---

## Cost Estimate (Phase 2 Added)

| Service | Phase 1 | Phase 2 | Total |
|---------|---------|---------|-------|
| Cognito | $0 | $0 | $0 (free tier: 50K MAUs) |
| DynamoDB | $0 | $2.50 | $2.50 |
| Lambda | $0.50 | $0.50 | $1.00 |
| API Gateway | $0 | $1.00 | $1.00 |
| S3 | $0.50 | $0 | $0.50 |
| SES | $0.30 | $0 | $0.30 |
| Anthropic API | $2.40 | $0 | $2.40 |
| CloudWatch | $1.00 | $0.50 | $1.50 |
| Secrets Manager | $0.40 | $0 | $0.40 |
| Other | $0.50 | $0 | $0.50 |
| **TOTAL** | ~$6 | ~$4.50 | **~$10.10/month** ✅ |

Still well under the $20/month budget!

---

## Next Steps: Phase 3

See `Documentation/MIGRATION_PLAN.md` for Phase 3 tasks:

1. Update daily Lambda to write reflections to DynamoDB
2. Implement dual Anthropic API calls (reflection + journaling prompt)
3. Integrate reflection generation with Reflections table
4. Update email service to query DynamoDB Users table for recipients
5. Test end-to-end reflection flow

**Estimated Time**: 1 week

---

## Support & Resources

- **Migration Plan**: `Documentation/MIGRATION_PLAN.md`
- **Phase 1 Guide**: `Documentation/PHASE1_SETUP_GUIDE.md`
- **Architecture**: `Documentation/ARCHITECTURE.md`
- **Security**: `Documentation/SECURITY.md`

---

**Last Updated**: November 1, 2024
**Phase**: 2 of 7
**Status**: Complete ✅
