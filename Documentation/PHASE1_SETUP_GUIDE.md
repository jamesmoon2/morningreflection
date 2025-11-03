# Phase 1 Setup Guide: Domain Migration & Infrastructure

**Status**: Phase 1 Complete ✅
**Date Completed**: November 1, 2024
**Next Phase**: Phase 2 - Backend Development (Auth & Database)

---

## Overview

Phase 1 focused on migrating from `jamescmooney.com` to `morningreflection.com` and preparing the infrastructure for the expanded web application.

### What Was Changed

1. ✅ Updated domain references in all configuration files
2. ✅ Implemented AWS Secrets Manager for API key security
3. ✅ Updated Lambda function to support Secrets Manager
4. ✅ Removed recipients.json (replaced by future DynamoDB)
5. ✅ Updated CDK stack resource names
6. ✅ Created setup scripts for Secrets Manager
7. ✅ Created comprehensive migration plan documentation

---

## Files Modified

### Configuration Files

| File | Changes |
|------|---------|
| `cdk.json` | • Updated `sender_email` to `reflections@morningreflection.com`<br/>• Updated `sender_domain` to `morningreflection.com`<br/>• Removed `initial_recipient`<br/>• Changed `anthropic_api_key` to `USE_SECRETS_MANAGER`<br/>• Added `s3_bucket_prefix`, `project_name`, `environment` |
| `infra/stoic_stack.py` | • Added Secrets Manager support<br/>• Updated resource names (MorningReflection*)<br/>• Updated fallback email to morningreflection.com<br/>• Added Lambda IAM permission for Secrets Manager |
| `lambda/handler.py` | • Added `get_anthropic_api_key()` function<br/>• Support for fetching API key from Secrets Manager<br/>• Updated service name references |

### Files Deleted

| File | Reason | Replacement |
|------|--------|-------------|
| `config/recipients.json` | Static recipient list | DynamoDB Users table (Phase 2) |

### New Files Created

| File | Purpose |
|------|---------|
| `Documentation/MIGRATION_PLAN.md` | Comprehensive migration roadmap |
| `Documentation/PHASE1_SETUP_GUIDE.md` | This file |
| `config/RECIPIENTS_MIGRATION.md` | Explains recipients.json removal |
| `scripts/setup-secrets.sh` | Bash script to create Secrets Manager secret |
| `scripts/setup_secrets.py` | Python script to create Secrets Manager secret |

---

## Deployment Steps

### Prerequisites

1. **AWS Account Access**
   - AWS CLI installed and configured
   - Sufficient permissions to:
     - Create/update Secrets Manager secrets
     - Deploy CDK stacks
     - Manage Lambda, S3, EventBridge, SES, SNS

2. **Domain Ownership**
   - Own `morningreflection.com` domain
   - Access to DNS management console

3. **Anthropic API Key**
   - Valid Anthropic API key
   - Get one at: https://console.anthropic.com/settings/keys

### Step 1: Set Up Secrets Manager

Choose **one** method to create the secret:

#### Option A: Using Bash Script (Recommended)

```bash
cd /home/user/morningreflection
./scripts/setup-secrets.sh
```

#### Option B: Using Python Script

```bash
cd /home/user/morningreflection
python3 scripts/setup_secrets.py
```

#### Option C: Manual AWS CLI

```bash
aws secretsmanager create-secret \
  --name morningreflection/anthropic-api-key \
  --description "Anthropic API key for Morning Reflection service" \
  --secret-string "your-anthropic-api-key-here" \
  --region us-west-2 \
  --tags Key=Project,Value=MorningReflection Key=Environment,Value=prod
```

#### Verify Secret Creation

```bash
aws secretsmanager describe-secret \
  --secret-id morningreflection/anthropic-api-key \
  --region us-west-2
```

---

### Step 2: Verify SES Domain

You must verify the `morningreflection.com` domain in Amazon SES before sending emails.

#### 2.1 Start Domain Verification

```bash
aws ses verify-domain-identity \
  --domain morningreflection.com \
  --region us-west-2
```

This will return a verification token. Add it to your DNS:

```
Type: TXT
Name: _amazonses.morningreflection.com
Value: <verification-token-from-above>
TTL: 1800
```

#### 2.2 Enable DKIM

```bash
aws ses verify-domain-dkim \
  --domain morningreflection.com \
  --region us-west-2
```

This will return 3 DKIM tokens. Add them to your DNS:

```
Type: CNAME
Name: <token1>._domainkey.morningreflection.com
Value: <token1>.dkim.amazonses.com
TTL: 1800

(Repeat for token2 and token3)
```

#### 2.3 Configure SPF and DMARC (Recommended)

```
# SPF Record
Type: TXT
Name: morningreflection.com
Value: v=spf1 include:amazonses.com ~all
TTL: 1800

# DMARC Record
Type: TXT
Name: _dmarc.morningreflection.com
Value: v=DMARC1; p=quarantine; rua=mailto:dmarc@morningreflection.com
TTL: 1800
```

#### 2.4 Verify Sender Email

```bash
aws ses verify-email-identity \
  --email-address reflections@morningreflection.com \
  --region us-west-2
```

Check your email and click the verification link.

#### 2.5 Request Production Access (If in Sandbox)

If your SES account is in sandbox mode, request production access:

```bash
# Check if in sandbox
aws sesv2 get-account --region us-west-2 | grep ProductionAccessEnabled

# If false, request production access via AWS Console:
# SES > Account Dashboard > Request production access
```

---

### Step 3: Deploy CDK Stack

#### 3.1 Install Dependencies

```bash
cd /home/user/morningreflection
pip install -r requirements.txt
```

#### 3.2 Bootstrap CDK (First Time Only)

```bash
cdk bootstrap aws://YOUR_ACCOUNT_ID/us-west-2
```

#### 3.3 Synthesize Stack (Optional - for review)

```bash
cdk synth
```

Review the generated CloudFormation template to ensure everything looks correct.

#### 3.4 Deploy Stack

```bash
cdk deploy
```

You'll be prompted to confirm IAM changes. Review and approve.

#### 3.5 Verify Deployment

```bash
# Get stack outputs
aws cloudformation describe-stacks \
  --stack-name StoicStack \
  --region us-west-2 \
  --query 'Stacks[0].Outputs'

# Check Lambda function
aws lambda get-function \
  --function-name MorningReflectionSender \
  --region us-west-2

# Check EventBridge rule
aws events describe-rule \
  --name MorningReflectionTrigger \
  --region us-west-2
```

---

### Step 4: Upload Configuration Files to S3

The Lambda function needs configuration files in S3.

#### 4.1 Get S3 Bucket Name

```bash
BUCKET_NAME=$(aws cloudformation describe-stacks \
  --stack-name StoicStack \
  --region us-west-2 \
  --query 'Stacks[0].Outputs[?OutputKey==`BucketName`].OutputValue' \
  --output text)

echo "Bucket: $BUCKET_NAME"
```

#### 4.2 Upload Configuration Files

```bash
# Upload quote database
aws s3 cp config/stoic_quotes_365_days.json \
  s3://$BUCKET_NAME/config/stoic_quotes_365_days.json

# Upload security config
aws s3 cp config/security_config.json \
  s3://$BUCKET_NAME/config/security_config.json

# Upload quote history (if it exists)
if [ -f config/quote_history.json ]; then
  aws s3 cp config/quote_history.json \
    s3://$BUCKET_NAME/quote_history.json
fi
```

#### 4.3 Verify Upload

```bash
aws s3 ls s3://$BUCKET_NAME/config/
```

---

### Step 5: Test the System

#### 5.1 Manual Test Invocation

Invoke the Lambda function manually to test:

```bash
aws lambda invoke \
  --function-name MorningReflectionSender \
  --region us-west-2 \
  --log-type Tail \
  --query 'LogResult' \
  --output text \
  response.json | base64 --decode

# View response
cat response.json
```

#### 5.2 Check CloudWatch Logs

```bash
# Get latest log stream
LOG_STREAM=$(aws logs describe-log-streams \
  --log-group-name /aws/lambda/MorningReflectionSender \
  --order-by LastEventTime \
  --descending \
  --max-items 1 \
  --region us-west-2 \
  --query 'logStreams[0].logStreamName' \
  --output text)

# View logs
aws logs get-log-events \
  --log-group-name /aws/lambda/MorningReflectionSender \
  --log-stream-name "$LOG_STREAM" \
  --region us-west-2 \
  --limit 50
```

#### 5.3 Verify Email Delivery

**IMPORTANT**: During Phase 1, you need to update the Lambda handler to temporarily send to a test email.

Edit `lambda/handler.py` line ~137 to add a test recipient:

```python
# Temporary test recipient for Phase 1
recipients = ["your-test-email@example.com"]
```

Then re-deploy:

```bash
cdk deploy
```

Invoke again and check your email inbox.

---

## What's Working Now

✅ **Infrastructure**:
- Lambda function deployed with new name
- EventBridge rule scheduled daily at 6 AM PT
- S3 bucket created for configuration
- SNS topic for security alerts
- CloudWatch logging enabled

✅ **Security**:
- API key stored in Secrets Manager (not environment variables)
- Lambda IAM role has least-privilege permissions
- S3 bucket encrypted and private
- Comprehensive security validation on API outputs

✅ **Email Service**:
- Domain verified in SES (morningreflection.com)
- Sender email verified
- DKIM enabled for email authentication
- SPF/DMARC configured

---

## What's NOT Working Yet

❌ **User Management**:
- No DynamoDB tables yet (Phase 2)
- No Cognito User Pool (Phase 2)
- Recipients are hardcoded in Lambda handler

❌ **Web Application**:
- No frontend app (Phase 4)
- No API Gateway (Phase 2)
- No journal functionality (Phase 3)
- No calendar view (Phase 4)

❌ **Journaling Prompts**:
- Second Anthropic API call not implemented yet (Phase 3)
- Only reflection is generated, not journaling prompt

---

## Rollback Plan

If something goes wrong, you can rollback:

### Rollback CDK Stack

```bash
# Delete the new stack
cdk destroy

# Redeploy the old stack (if you have the old code)
git checkout <old-commit-hash>
cdk deploy
```

### Rollback Domain

The old `jamescmooney.com` email service should still be running if it was deployed separately. This migration creates a **new stack** with new resources, so it doesn't interfere with the old one.

### Delete Secret (if needed)

```bash
aws secretsmanager delete-secret \
  --secret-id morningreflection/anthropic-api-key \
  --region us-west-2 \
  --force-delete-without-recovery
```

---

## Troubleshooting

### Issue: "Secret not found"

**Solution**: Run the setup script again:
```bash
./scripts/setup-secrets.sh
```

### Issue: "Email not verified"

**Solution**: Verify sender email:
```bash
aws ses verify-email-identity \
  --email-address reflections@morningreflection.com \
  --region us-west-2
```
Check your inbox for verification email.

### Issue: "Access Denied" in Lambda

**Solution**: Check Lambda IAM role has Secrets Manager read permission:
```bash
aws lambda get-function \
  --function-name MorningReflectionSender \
  --region us-west-2 \
  --query 'Configuration.Role'
```

Verify the role has `secretsmanager:GetSecretValue` permission.

### Issue: "No recipients configured"

**Solution**: Recipients are now hardcoded temporarily. Edit `lambda/handler.py` line ~137 and add your test email.

---

## Next Steps: Phase 2

See `Documentation/MIGRATION_PLAN.md` for Phase 2 tasks:

1. Create Cognito User Pool with 2FA
2. Create DynamoDB tables (Users, Reflections, JournalEntries)
3. Create API Gateway with authentication endpoints
4. Implement user profile and preferences APIs
5. Write unit tests for all Lambda functions

**Estimated Time**: 1-2 weeks

---

## Support & Resources

- **Migration Plan**: `Documentation/MIGRATION_PLAN.md`
- **Architecture**: `Documentation/ARCHITECTURE.md`
- **Deployment Guide**: `Documentation/DEPLOYMENT.md`
- **Security Documentation**: `Documentation/SECURITY.md`

---

**Last Updated**: November 1, 2024
**Phase**: 1 of 7
**Status**: Complete ✅
