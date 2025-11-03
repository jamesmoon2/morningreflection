# Morning Reflection Migration & Expansion Plan

**Project**: Morning Reflection Web Application
**Domain**: morningreflection.com
**Start Date**: November 1, 2024
**Target Budget**: <$20/month
**Security Level**: Enterprise-grade

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Architecture Overview](#architecture-overview)
3. [Migration Strategy](#migration-strategy)
4. [New Features](#new-features)
5. [Database Schema](#database-schema)
6. [API Design](#api-design)
7. [Security Architecture](#security-architecture)
8. [Implementation Phases](#implementation-phases)
9. [Cost Analysis](#cost-analysis)
10. [Risk Assessment](#risk-assessment)

---

## Executive Summary

### Goals

- **Migrate** from jamescmooney.com to morningreflection.com
- **Expand** from email-only service to full web application
- **Add** user accounts, journaling, calendar view, and preferences
- **Maintain** enterprise-grade security (2FA, encryption, audit logging)
- **Keep** costs under $20/month

### Key Decisions

| Decision | Choice |
|----------|--------|
| Architecture | Serverless (AWS) |
| Budget | $12-17/month (estimated) |
| 2FA | Optional (user choice) |
| Frontend | React SPA (Vite) |
| Backend | API Gateway + Lambda + DynamoDB |
| Auth | Amazon Cognito |
| Domain | morningreflection.com (owned) |

---

## Architecture Overview

### Technology Stack

**Frontend**:
- React 18+ with TypeScript
- Vite (build tool)
- Tailwind CSS (styling)
- React Router (navigation)
- Axios (HTTP client)
- Hosted on AWS Amplify

**Backend**:
- API Gateway (REST API)
- Lambda (Python 3.12)
- DynamoDB (NoSQL database)
- Cognito (authentication + 2FA)
- Secrets Manager (API keys)
- S3 (reflections archive)
- SES (email delivery)

**External Services**:
- Anthropic Claude API (reflections + prompts)
- CloudWatch (monitoring + logs)
- SNS (security alerts)

### Architecture Diagram

```
┌────────────────────┐
│   User Browser     │
│ app.morningreflection.com
└────────┬───────────┘
         │ HTTPS/TLS 1.3
         ▼
┌────────────────────┐
│  AWS Amplify       │ ← React SPA, CloudFront CDN
└────────┬───────────┘
         │ REST API
         ▼
┌────────────────────┐
│  API Gateway       │ ← /auth, /user, /reflections, /journal
└────┬───────┬───────┘
     │       │
     ▼       ▼
┌─────────┐ ┌─────────────┐
│ Cognito │ │   Lambda    │ ← Python 3.12 handlers
└─────────┘ └──────┬──────┘
                   │
         ┌─────────┼─────────┐
         ▼         ▼         ▼
    ┌─────────┐ ┌───────┐ ┌────────┐
    │DynamoDB │ │   S3  │ │  SES   │
    └─────────┘ └───────┘ └────────┘
```

---

## Migration Strategy

### Phase 1: Domain & Infrastructure Changes

#### 1.1 Domain References

**Files to Update**:

| File | Old Value | New Value |
|------|-----------|-----------|
| `cdk.json` | `sender_domain: "jamescmooney.com"` | `sender_domain: "morningreflection.com"` |
| `cdk.json` | `sender_email: "reflections@jamescmooney.com"` | `sender_email: "reflections@morningreflection.com"` |
| `cdk.json` | `initial_recipient: "jamesmoon2@gmail.com"` | Remove (DynamoDB-based) |
| `infra/stoic_stack.py` | Line 74 fallback email | `reflections@morningreflection.com` |

#### 1.2 S3 Bucket Migration

**Problem**: S3 buckets cannot be renamed. Must create new bucket.

**Solution**:
1. Create new bucket: `morningreflection-prod-<random-suffix>`
2. Copy data from old bucket to new bucket
3. Update CDK stack references
4. Keep old bucket for 30 days as backup

**New S3 Structure**:
```
s3://morningreflection-prod-<suffix>/
├── config/
│   ├── stoic_quotes_365_days.json
│   └── security_config.json
├── reflections/              # NEW
│   └── YYYY/MM/DD/
│       ├── reflection.json
│       └── prompt.json
├── users/                    # NEW
│   └── {user_id}/
│       └── journal/
│           └── YYYY-MM-DD.json
├── quote_history.json
└── security/
    ├── response_statistics.json
    └── audit_logs/
```

#### 1.3 API Key Security

**Current**: API key in `cdk.json` (insecure)
**New**: AWS Secrets Manager

```bash
aws secretsmanager create-secret \
  --name morningreflection/anthropic-api-key \
  --secret-string "your-api-key-here" \
  --region us-west-2
```

Update Lambda to fetch from Secrets Manager:
```python
import boto3
import json

def get_anthropic_api_key():
    client = boto3.client('secretsmanager', region_name='us-west-2')
    response = client.get_secret_value(SecretId='morningreflection/anthropic-api-key')
    return json.loads(response['SecretString'])
```

#### 1.4 Files to Delete

**Remove** (prevent production conflicts):
- `config/recipients.json` → Replace with DynamoDB Users table
- Old S3 bucket references in CDK

#### 1.5 SES Domain Verification

**Steps**:
1. Verify domain in SES (us-west-2)
2. Add DNS records:
   - TXT: SES verification token
   - 3× CNAME: DKIM signatures
3. Verify sender email: `reflections@morningreflection.com`
4. Request production access (if still in sandbox)
5. Configure SPF/DMARC records

**DNS Records**:
```
# SPF
morningreflection.com.  TXT  "v=spf1 include:amazonses.com ~all"

# DMARC
_dmarc.morningreflection.com.  TXT  "v=DMARC1; p=quarantine; rua=mailto:dmarc@morningreflection.com"

# DKIM (3 records from SES console)
<token1>._domainkey.morningreflection.com.  CNAME  <token1>.dkim.amazonses.com
<token2>._domainkey.morningreflection.com.  CNAME  <token2>.dkim.amazonses.com
<token3>._domainkey.morningreflection.com.  CNAME  <token3>.dkim.amazonses.com
```

---

## New Features

### 1. User Accounts & Authentication

**Features**:
- Email/password signup with verification
- Login with JWT tokens
- Optional 2FA (TOTP via Google Authenticator, Authy)
- Password reset via email
- Account deletion (GDPR compliance)

**Implementation**: Amazon Cognito User Pool

**Password Policy**:
- Minimum 12 characters
- Require: uppercase, lowercase, numbers, symbols
- Password history: 5
- Compromised credential check: Enabled

### 2. User Preferences

**Configurable Settings**:
- Delivery time (local timezone, e.g., "06:00")
- Timezone (e.g., "America/Los_Angeles")
- Email enabled/disabled
- Weekly digest opt-in
- Notification preferences

**Storage**: DynamoDB Users table

### 3. Journaling Feature

**Capabilities**:
- Daily journal entries (one per date)
- Rich text or plain text input
- Auto-save (debounced)
- Word count tracking
- Character limit: 10,000 chars
- Edit/delete entries

**Security**:
- Input sanitization (XSS protection)
- Malicious pattern detection
- Character validation (homoglyphs, repetition)

**Storage**: DynamoDB JournalEntries table

### 4. Calendar View

**Features**:
- Monthly grid view
- Visual indicators:
  - Green dot: Reflection available
  - Blue dot: Journal entry exists
- Click date → View reflection + journal
- Navigate between months
- Today highlight

**API**: `GET /reflections/calendar?month=YYYY-MM`

### 5. Dual Anthropic API Calls

**Call 1**: Daily reflection (existing)
- Input: Quote, attribution, theme
- Output: 250-450 word reflection
- Model: claude-sonnet-4-5-20250929

**Call 2**: Journaling prompt (NEW)
- Input: Reflection, quote, theme
- Output: 1-2 sentence journaling prompt
- Model: claude-sonnet-4-5-20250929
- Max tokens: 200

**Cost Impact**: +$0.05/month (negligible)

### 6. Email Magic Links

**User Flow**:
1. User receives daily email
2. Email contains link: `https://app.morningreflection.com/daily/2024-11-01?token=<JWT>`
3. Click → Auto-login (if logged out)
4. Lands on today's reflection + journal editor

**Implementation**:
- Generate time-limited JWT (15-minute expiration)
- JWT claims: `user_id`, `date`, `action: "daily_reflection"`
- Frontend validates token, exchanges for Cognito session

---

## Database Schema

### Table 1: MorningReflection-Users

**Partition Key**: `user_id` (String, UUID)
**GSI**: `Email-index` on `email` (for login lookups)

| Attribute | Type | Description |
|-----------|------|-------------|
| user_id | String (UUID) | Primary key (Cognito sub) |
| email | String | User email address |
| email_verified | Boolean | Verification status |
| created_at | String (ISO 8601) | Account creation |
| preferences | Map | User preferences (see below) |
| subscription_status | String | `active`, `paused`, `cancelled` |
| timezone | String | e.g., `America/Los_Angeles` |
| delivery_time | String | e.g., `06:00` (local time) |
| last_login | String (ISO 8601) | Last login timestamp |

**preferences Map**:
```json
{
  "delivery_time": "06:00",
  "timezone": "America/Los_Angeles",
  "email_enabled": true,
  "web_only": false,
  "reminder_enabled": false,
  "weekly_digest": false
}
```

---

### Table 2: MorningReflection-Reflections

**Partition Key**: `date` (String, YYYY-MM-DD)

| Attribute | Type | Description |
|-----------|------|-------------|
| date | String (YYYY-MM-DD) | Reflection date (PK) |
| quote | String | Stoic quote |
| attribution | String | Quote author |
| theme | String | Monthly theme |
| reflection | String | Generated reflection (250-450 words) |
| journaling_prompt | String | Generated journaling prompt |
| generated_at | String (ISO 8601) | Generation timestamp |
| model_version | String | Claude model used |
| security_report | Map | Security validation results |

---

### Table 3: MorningReflection-JournalEntries

**Partition Key**: `user_id` (String, UUID)
**Sort Key**: `date` (String, YYYY-MM-DD)

| Attribute | Type | Description |
|-----------|------|-------------|
| user_id | String (UUID) | User identifier (PK) |
| date | String (YYYY-MM-DD) | Journal entry date (SK) |
| entry | String | Journal text (max 10K chars) |
| word_count | Number | Entry word count |
| created_at | String (ISO 8601) | Creation timestamp |
| updated_at | String (ISO 8601) | Last edit timestamp |

**Access Patterns**:
- Get all entries for user: Query on `user_id`
- Get entry for specific date: Query on `user_id` + `date`
- Get entries in date range: Query with `date` BETWEEN

---

## API Design

### Authentication Endpoints (Cognito-managed)

- `POST /auth/signup` - Create account
- `POST /auth/login` - Login (returns JWT)
- `POST /auth/mfa/setup` - Enable TOTP 2FA
- `POST /auth/mfa/verify` - Verify TOTP code
- `POST /auth/forgot-password` - Password reset
- `POST /auth/refresh` - Refresh JWT token

### User Endpoints

- `GET /user/profile` - Get user details
- `PUT /user/profile` - Update profile
- `PUT /user/preferences` - Update delivery preferences
- `DELETE /user/account` - Delete account (with confirmation)

### Reflection Endpoints

- `GET /reflections/today` - Get today's reflection + prompt
- `GET /reflections/{YYYY-MM-DD}` - Get reflection by date
- `GET /reflections/calendar?month=YYYY-MM` - Get calendar metadata

### Journal Endpoints

- `POST /journal` - Create/update journal entry
  - Body: `{ "date": "YYYY-MM-DD", "entry": "..." }`
- `GET /journal/{YYYY-MM-DD}` - Get journal entry for date
- `GET /journal/list?from=YYYY-MM-DD&to=YYYY-MM-DD` - List entries in range
- `DELETE /journal/{YYYY-MM-DD}` - Delete journal entry

### API Security

- **Authorization**: Cognito JWT authorizer (all endpoints except `/auth/*`)
- **Rate Limiting**:
  - Per-user: 100 requests/minute
  - Anonymous: 10 requests/minute (auth endpoints only)
- **Request Validation**: JSON schema validation on all POST/PUT
- **CORS**: Configured for `app.morningreflection.com`

---

## Security Architecture

### 1. Authentication & Authorization

**Amazon Cognito User Pool**:
- Password policy: 12+ chars, uppercase, lowercase, numbers, symbols
- MFA: Optional TOTP (Google Authenticator, Authy)
- Account recovery: Email-based password reset (15-minute token)
- Session management: 1-hour access token, 30-day refresh token
- Compromised credentials check: Enabled
- Adaptive authentication: Block suspicious IPs
- Device tracking: Remember trusted devices (30 days)

### 2. Data Encryption

**In Transit (TLS 1.3)**:
- CloudFront: TLS 1.3, modern cipher suites only
- API Gateway: TLS 1.2+ enforced
- SES: TLS for email transport
- Anthropic API: HTTPS (TLS 1.2+)

**At Rest**:
- **DynamoDB**: AWS-managed KMS key (AES-256-GCM)
  - Point-in-time recovery: Enabled (35-day retention)
- **S3**: SSE-S3 (AES-256) or SSE-KMS
  - Versioning: Enabled
  - Object Lock: Optional (audit logs)
- **Secrets Manager**: KMS-encrypted secrets
- **CloudWatch Logs**: KMS-encrypted log groups

### 3. Input Validation

**Reuse Existing Security Modules** (`lambda/security.py`):
- `ContentSanitizer` - Remove control chars, normalize whitespace
- `MaliciousPatternDetector` - Detect XSS, SQL injection, scripts
- `URLDetector` - Block all URLs (configurable)
- `CharacterValidator` - Detect homoglyphs, repetition

**Journal Entry Validation**:
```python
def validate_journal_entry(entry: str) -> Dict[str, Any]:
    sanitized = ContentSanitizer().sanitize(entry)
    patterns_result = MaliciousPatternDetector().check_content(sanitized)
    if patterns_result["has_malicious_patterns"]:
        raise ValidationError("Prohibited content detected")
    if len(sanitized) > 10000:
        raise ValidationError("Exceeds 10,000 character limit")
    char_result = CharacterValidator().validate(sanitized)
    if not char_result["valid"]:
        raise ValidationError(f"Invalid characters: {char_result['reason']}")
    return {"sanitized_entry": sanitized, "word_count": len(sanitized.split())}
```

### 4. Audit Logging

**Reuse Existing** (`lambda/security_logging.py`):
- `SecurityLogger` - Structured logging with correlation IDs
- `ContentRedactor` - Redact API keys, tokens, passwords
- S3 audit trail persistence

**NEW: User Activity Logging**:
```json
{
  "user_id": "abc-123",
  "action": "journal_entry_created",
  "timestamp": "2024-11-01T14:23:45Z",
  "ip_address": "203.0.113.42",
  "user_agent": "Mozilla/5.0...",
  "resource": "/journal/2024-11-01",
  "status": "success",
  "correlation_id": "req-xyz-789"
}
```

### 5. Monitoring & Alerting

**CloudWatch Alarms**:
- Failed login attempts > 10/minute
- 4xx error rate > 5%
- 5xx error rate > 1%
- Lambda errors > 10/hour
- DynamoDB throttled requests > 0
- Anthropic API failures > 5%

**SNS Alerts** (reuse `lambda/security_alerting.py`):
- Security events → Email + SMS (critical only)
- System errors → Email
- Daily summary → Email

### 6. GDPR Compliance

- **Data minimization**: Only collect necessary data
- **Right to access**: API endpoint to export user data (JSON)
- **Right to deletion**: `DELETE /user/account` → Hard delete
- **Data retention**: User-controlled (journal), 1 year (audit logs)
- **Cookie consent**: Required for EU users

---

## Implementation Phases

### Phase 1: Migration & Infrastructure (Week 1-2)

**Objectives**:
- Migrate domain from jamescmooney.com to morningreflection.com
- Secure API keys with Secrets Manager
- Create new S3 bucket and migrate data
- Verify SES domain and DKIM
- Deploy updated Lambda with new environment variables

**Tasks**:
1. ✅ Update `cdk.json` with new domain values
2. ✅ Move Anthropic API key to Secrets Manager
3. ✅ Create new S3 bucket (`morningreflection-prod-<suffix>`)
4. ✅ Migrate data from old bucket to new bucket
5. ✅ Update `infra/stoic_stack.py` with new environment variables
6. ✅ Delete `config/recipients.json` (replaced by DynamoDB)
7. ✅ Update documentation files with new domain
8. ✅ Verify SES domain + DKIM setup
9. ✅ Deploy CDK stack with new configuration
10. ✅ Smoke test: Verify daily reflection email works

**Deliverables**:
- Updated CDK stack deployed
- morningreflection.com sending emails successfully
- Old jamescmooney.com service still running (no conflicts)

---

### Phase 2: Backend - Auth & Database (Week 3-4)

**Objectives**:
- Set up Cognito User Pool with 2FA
- Create DynamoDB tables
- Implement authentication APIs
- Implement user preferences APIs

**Tasks**:
1. Create Cognito User Pool with 2FA enabled
2. Configure password policy, MFA, adaptive auth
3. Create DynamoDB tables (Users, Reflections, JournalEntries)
4. Enable encryption, point-in-time recovery, backups
5. Create API Gateway with REST API endpoints
6. Implement Lambda functions:
   - `POST /auth/signup`
   - `POST /auth/login`
   - `POST /auth/mfa/setup`
   - `POST /auth/mfa/verify`
   - `GET /user/profile`
   - `PUT /user/preferences`
7. Implement Cognito authorizer on API Gateway
8. Unit tests for all Lambda functions

**Deliverables**:
- Working authentication system (signup, login, 2FA)
- User preferences API
- Cognito + DynamoDB integration

---

### Phase 3: Backend - Reflections & Journaling (Week 4-5)

**Objectives**:
- Migrate reflection generation to DynamoDB
- Implement journaling prompt generation
- Create reflection and journal APIs
- Update email service with magic links

**Tasks**:
1. Migrate reflection generation to DynamoDB storage
2. Implement journaling prompt generation (2nd Anthropic call)
3. Create API endpoints:
   - `GET /reflections/today`
   - `GET /reflections/{date}`
   - `GET /reflections/calendar?month=YYYY-MM`
   - `POST /journal`
   - `GET /journal/{date}`
   - `GET /journal/list?from=X&to=Y`
   - `DELETE /journal/{date}`
4. Implement journal entry validation
5. Update EventBridge Lambda:
   - Query DynamoDB for users with matching delivery time
   - Generate reflection + prompt
   - Store in DynamoDB
   - Send batch emails (SES)
6. Implement magic link generation
7. Unit and integration tests

**Deliverables**:
- Reflection API working
- Journal API working
- Updated email service with magic links
- Security validation on all inputs

---

### Phase 4: Frontend Development (Week 5-6)

**Objectives**:
- Build React SPA with Vite
- Implement authentication UI
- Implement main app pages
- Integrate with API Gateway

**Tasks**:
1. Set up React app with Vite + TypeScript
2. Implement authentication UI:
   - Login page
   - Signup page
   - 2FA setup page
   - Password reset flow
3. Implement main app pages:
   - Dashboard (today's reflection + journal)
   - Calendar view
   - Journal entry page
   - Settings page
4. Implement magic link landing page
5. Integrate with API Gateway (Axios)
6. JWT token management (httpOnly cookies)
7. Loading states, error handling, notifications
8. Responsive design (mobile-first)
9. Accessibility (WCAG 2.1 AA)

**Technology Choices**:
- Framework: Vite + React 18
- Styling: Tailwind CSS
- State Management: React Context or Zustand
- HTTP Client: Axios
- UI Library: shadcn/ui or Radix UI
- Calendar: react-calendar or date-fns

**Deliverables**:
- Fully functional React app
- All user flows working
- Mobile-responsive design
- Accessible UI

---

### Phase 5: Deployment & Infrastructure (Week 7)

**Objectives**:
- Deploy frontend to AWS Amplify
- Configure custom domain
- Set up monitoring and alerts
- Configure CI/CD pipeline

**Tasks**:
1. Set up AWS Amplify Hosting
2. Configure custom domain: `app.morningreflection.com`
3. Set up ACM certificate for HTTPS
4. Configure CloudFront CDN settings
5. Configure CORS on API Gateway
6. Set up CloudWatch dashboards
7. Set up CloudWatch Alarms (SNS alerts)
8. Configure CI/CD pipeline (GitHub Actions):
   - Frontend: Auto-deploy on push to main
   - Backend: CDK deploy on push to main

**Deliverables**:
- Production app live at `app.morningreflection.com`
- Monitoring dashboards operational
- Automated deployments working

---

### Phase 6: Testing & Security Audit (Week 8)

**Objectives**:
- End-to-end testing
- Security testing (OWASP Top 10)
- Performance testing
- Accessibility audit

**Tasks**:
1. E2E testing (Playwright):
   - User signup flow
   - Login + 2FA flow
   - Journal creation/editing
   - Calendar navigation
   - Magic link from email
2. Security testing:
   - OWASP Top 10 checks
   - 2FA bypass attempts
   - Rate limiting tests
   - CSRF attacks
3. Performance testing:
   - Load test API Gateway (100 concurrent users)
   - Test Lambda cold starts
   - Test DynamoDB throughput
4. Accessibility audit (WAVE, Lighthouse)
5. Browser compatibility testing
6. Mobile testing

**Tools**:
- Security: OWASP ZAP, Burp Suite, npm audit
- Performance: Apache JMeter, Artillery.io
- E2E: Playwright, Cypress
- Accessibility: axe DevTools, WAVE, Lighthouse

**Deliverables**:
- Security audit report
- Performance test results
- Accessibility compliance report
- Test coverage report (>80%)

---

### Phase 7: Beta Launch & Monitoring (Week 8+)

**Objectives**:
- Launch beta with small user group
- Monitor performance and errors
- Gather user feedback
- Iterate on bugs and UX

**Tasks**:
1. Invite beta users (start with 10-20 people)
2. Monitor CloudWatch metrics daily
3. Monitor error logs, security alerts
4. Gather user feedback
5. Fix critical bugs within 24 hours
6. Iterate on UI/UX
7. Document operational runbooks

**Success Criteria**:
- Zero security incidents
- <1% error rate
- <2 second page load time
- Positive user feedback (NPS >50)
- 99.9% uptime for daily reflections

---

## Cost Analysis

### Monthly Cost Breakdown (100 active users)

| Service | Usage Estimate | Monthly Cost |
|---------|----------------|--------------|
| **Cognito** | 100 active users | $0 (free tier: 50K MAUs) |
| **DynamoDB** | 25 GB storage, 10K reads/day, 500 writes/day | $2.50 |
| **Lambda** | 10K invocations/day | $0.50 |
| **API Gateway** | 10K requests/day | $1.00 |
| **Amplify Hosting** | 5 GB transfer, 10 builds/month | $2.00 |
| **S3** | 10 GB storage, 100K requests/month | $0.50 |
| **SES** | 3,000 emails/month | $0.30 |
| **Anthropic API** | 120 API calls/month @ $0.02/call | $2.40 |
| **CloudWatch** | 1 GB logs, metrics, alarms | $1.00 |
| **Secrets Manager** | 1 secret | $0.40 |
| **Route 53** | Hosted zone | $0.50 |
| **SNS** | 100 notifications/month | $0.01 |
| **ACM** | TLS certificates | $0 (free) |
| **KMS** | Customer-managed keys (optional) | $1.00 |
| **TOTAL** | | **$12.11/month** ✅ |

### Scaling Estimates (1,000 users)

| Service | Monthly Cost |
|---------|--------------|
| Anthropic API | $24 (600 reflections × 2 calls) |
| DynamoDB | $5 (more reads/writes) |
| SES | $3 (30K emails) |
| Lambda/API Gateway | $3 (10x requests) |
| Other services | $5 (unchanged) |
| **TOTAL** | **$40-45/month** |

---

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| **SES verification fails** | Low | High | Test in sandbox first, have backup provider |
| **Anthropic API rate limits** | Medium | Medium | Implement backoff, cache reflections |
| **Lambda cold starts** | Medium | Low | Provisioned concurrency for critical functions |
| **DynamoDB throttling** | Low | Medium | Enable auto-scaling, monitor capacity |
| **Security breach** | Low | Critical | Input validation, security testing, bug bounty |
| **User data loss** | Low | Critical | Point-in-time recovery, daily S3 backups |
| **Cost overrun** | Medium | Low | CloudWatch billing alarms at $15, $20, $25 |
| **2FA lockout** | Medium | Medium | Backup codes, SMS fallback, admin recovery |
| **Email deliverability** | Medium | High | SPF/DKIM/DMARC, monitor SES reputation |
| **Migration breaks old service** | Low | High | Deploy to separate environment first |

---

## Success Metrics

### Technical Metrics
- API latency (p95): <500ms
- Error rate: <1%
- Uptime: 99.9%
- Email delivery rate: >98%

### Security Metrics
- Zero successful attacks
- Zero data breaches
- 2FA adoption: >50% within 3 months
- Password strength: >80 (zxcvbn score)

### User Engagement
- DAU/MAU ratio: >30%
- Journal entries/week: >3 per user
- Magic link CTR: >40%
- 30-day retention: >60%

### Business Metrics
- Monthly cost: <$20
- Cost per user: <$0.20
- User growth: +10% MoM

---

## Post-Launch Roadmap

### Phase 2 Features (3-6 months)
- Mobile app (React Native)
- Social features (share reflections)
- Streaks (consecutive days journaling)
- Multiple themes (Stoicism, Buddhism, etc.)
- Push notifications (mobile)
- Personal analytics (word count trends)
- Export (PDF, Markdown)

### Phase 3 Features (6-12 months)
- Subscription model ($5/month premium)
- Community forums
- Guided journaling programs
- Integrations (Notion, Obsidian)
- Voice journaling
- Internationalization (Spanish, French, German)

---

## Appendices

### A. Environment Variables

**Lambda (Daily Reflection)**:
```python
{
    "SENDER_EMAIL": "reflections@morningreflection.com",
    "SENDER_DOMAIN": "morningreflection.com",
    "S3_BUCKET": "morningreflection-prod-<suffix>",
    "DYNAMODB_USERS_TABLE": "MorningReflection-Users",
    "DYNAMODB_REFLECTIONS_TABLE": "MorningReflection-Reflections",
    "ANTHROPIC_SECRET_NAME": "morningreflection/anthropic-api-key",
    "WEB_APP_URL": "https://app.morningreflection.com"
}
```

**Lambda (API Handlers)**:
```python
{
    "DYNAMODB_USERS_TABLE": "MorningReflection-Users",
    "DYNAMODB_REFLECTIONS_TABLE": "MorningReflection-Reflections",
    "DYNAMODB_JOURNAL_TABLE": "MorningReflection-JournalEntries",
    "S3_BUCKET": "morningreflection-prod-<suffix>",
    "COGNITO_USER_POOL_ID": "<pool-id>",
    "ANTHROPIC_SECRET_NAME": "morningreflection/anthropic-api-key"
}
```

### B. CDK Context Variables (cdk.json)

```json
{
  "anthropic_api_key": "USE_SECRETS_MANAGER",
  "sender_email": "reflections@morningreflection.com",
  "sender_domain": "morningreflection.com",
  "s3_bucket_name": "morningreflection-prod",
  "project_name": "MorningReflection",
  "environment": "prod"
}
```

### C. Required DNS Records

**SES Verification**:
```
# Domain verification
_amazonses.morningreflection.com.  TXT  "<verification-token>"

# DKIM (3 records from SES console)
<token1>._domainkey.morningreflection.com.  CNAME  <token1>.dkim.amazonses.com
<token2>._domainkey.morningreflection.com.  CNAME  <token2>.dkim.amazonses.com
<token3>._domainkey.morningreflection.com.  CNAME  <token3>.dkim.amazonses.com

# SPF
morningreflection.com.  TXT  "v=spf1 include:amazonses.com ~all"

# DMARC
_dmarc.morningreflection.com.  TXT  "v=DMARC1; p=quarantine; rua=mailto:dmarc@morningreflection.com"
```

**Amplify Custom Domain**:
```
# From AWS Amplify console
app.morningreflection.com.  CNAME  <amplify-distribution>.cloudfront.net
```

---

## Contact & Support

**Project Owner**: James Moon
**Repository**: https://github.com/jamesmoon2/morningreflection
**Documentation**: `/Documentation/`

**Key Documents**:
- `README.md` - Project overview
- `ARCHITECTURE.md` - System architecture
- `DEPLOYMENT.md` - Deployment guide
- `SECURITY.md` - Security controls
- `MAINTENANCE.md` - Operations guide
- `MIGRATION_PLAN.md` - This document

---

**Last Updated**: November 1, 2024
**Version**: 1.0
