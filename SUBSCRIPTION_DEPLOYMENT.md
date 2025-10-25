# Subscription Feature - Deployment Guide

This guide walks through deploying the subscription management features to your Daily Stoic Reflection service.

## Prerequisites

Before deploying, ensure you have:

- ✅ AWS CLI configured with appropriate credentials
- ✅ AWS CDK installed (`npm install -g aws-cdk`)
- ✅ Python 3.12+ installed
- ✅ Domain `jamescmooney.com` configured and verified in SES
- ✅ Existing Daily Stoic Reflection service deployed
- ✅ S3 bucket hosting your static website

## Deployment Overview

The subscription feature adds the following components:

1. **DynamoDB Table**: `StoicSubscribers` - Stores subscriber information
2. **API Gateway**: REST API with endpoints for subscribe/unsubscribe/confirm
3. **Subscription Lambda**: Handles API requests
4. **Updated Daily Lambda**: Reads subscribers from DynamoDB
5. **Website Forms**: HTML forms for subscription management

## Step-by-Step Deployment

### Step 1: Update CDK Dependencies

First, ensure all required CDK dependencies are installed:

```bash
cd /path/to/MorningMeditations

# Install/update requirements
pip install -r requirements.txt

# Bootstrap CDK if not already done
cdk bootstrap
```

### Step 2: Update cdk.json (Optional)

Add the website URL to your `cdk.json` context (optional, defaults to https://jamescmooney.com):

```json
{
  "context": {
    "anthropic_api_key": "your-api-key",
    "sender_email": "reflections@jamescmooney.com",
    "website_url": "https://jamescmooney.com"
  }
}
```

### Step 3: Review Infrastructure Changes

Preview the changes that will be deployed:

```bash
cdk diff
```

This will show:
- New DynamoDB table creation
- New Lambda function for subscriptions
- New API Gateway resources
- Updated permissions for existing Lambda

### Step 4: Deploy Infrastructure

Deploy the updated infrastructure:

```bash
cdk deploy
```

**Important:** Take note of the CloudFormation outputs, especially:
- `ApiUrl` - Your API Gateway URL (e.g., `https://abc123.execute-api.us-west-2.amazonaws.com/prod/`)
- `TableName` - DynamoDB table name (should be `StoicSubscribers`)

Example output:
```
Outputs:
StoicStack.ApiUrl = https://abc123xyz.execute-api.us-west-2.amazonaws.com/prod/
StoicStack.TableName = StoicSubscribers
StoicStack.BucketName = stoicstack-stoicbucket12345-abcdef
```

### Step 5: Configure Environment Variables

Update the Daily Sender Lambda with the API URL for unsubscribe links:

```bash
# Get the API URL from the stack outputs
API_URL=$(aws cloudformation describe-stacks \
  --stack-name StoicStack \
  --query 'Stacks[0].Outputs[?OutputKey==`ApiUrl`].OutputValue' \
  --output text)

# Update Lambda environment variable
aws lambda update-function-configuration \
  --function-name DailyStoicSender \
  --environment Variables={BUCKET_NAME=your-bucket-name,TABLE_NAME=StoicSubscribers,SENDER_EMAIL=reflections@jamescmooney.com,ANTHROPIC_API_KEY=your-key,API_URL=$API_URL}
```

### Step 6: Migrate Existing Recipients

Migrate your existing recipients from S3 to DynamoDB:

```bash
cd scripts

# First, do a dry run to see what would happen
python migrate_subscribers.py --dry-run

# If everything looks good, run the actual migration
python migrate_subscribers.py

# Follow the prompts and confirm migration
```

The script will:
1. Read `recipients.json` from S3
2. Create a backup file locally
3. Import each email to DynamoDB with `status: active`
4. Skip emails that already exist
5. Show a summary of results

### Step 7: Update Website Forms

Upload the subscription forms to your S3 website bucket:

```bash
# Update API URL in the JavaScript file
cd website/js
# Edit subscription.js and confirm.html to replace API_GATEWAY_URL_HERE with your actual API URL

# Replace the placeholder with actual API URL
sed -i "s|API_GATEWAY_URL_HERE|$API_URL|g" subscription.js
sed -i "s|API_GATEWAY_URL_HERE|$API_URL|g" ../confirm.html

cd ..

# Upload files to S3 bucket
aws s3 sync . s3://your-website-bucket/ \
  --exclude "*" \
  --include "*.html" \
  --include "css/*" \
  --include "js/*" \
  --acl public-read
```

**Alternative: Manual Update**

1. Open `website/js/subscription.js`
2. Replace `API_GATEWAY_URL_HERE` with your actual API URL
3. Open `website/confirm.html`
4. Replace `API_GATEWAY_URL_HERE` with your actual API URL
5. Upload all files in `website/` directory to your S3 bucket

### Step 8: Configure S3 Website Hosting

Ensure your S3 bucket is configured for static website hosting:

```bash
aws s3 website s3://your-website-bucket/ \
  --index-document index.html \
  --error-document error.html
```

Make sure the subscription pages are publicly accessible:

```bash
aws s3api put-object-acl \
  --bucket your-website-bucket \
  --key subscribe.html \
  --acl public-read
```

### Step 9: Test the Subscription Flow

#### Test 1: Subscribe

1. Visit `https://jamescmooney.com/subscribe.html`
2. Enter a test email address
3. Click "Subscribe"
4. Verify you receive a confirmation email
5. Click the confirmation link in the email
6. Verify you see the success page

#### Test 2: Verify in DynamoDB

```bash
# Check that subscriber was created
aws dynamodb get-item \
  --table-name StoicSubscribers \
  --key '{"email": {"S": "your-test-email@example.com"}}'

# List all active subscribers
aws dynamodb scan \
  --table-name StoicSubscribers \
  --filter-expression "#status = :active" \
  --expression-attribute-names '{"#status": "status"}' \
  --expression-attribute-values '{":active": {"S": "active"}}'
```

#### Test 3: Receive Daily Email

Wait for the next scheduled email (6 AM PT) or manually invoke the Lambda:

```bash
aws lambda invoke \
  --function-name DailyStoicSender \
  --payload '{}' \
  response.json

cat response.json
```

Verify the email includes an unsubscribe link.

#### Test 4: Unsubscribe

1. Click the unsubscribe link in the email
2. Confirm unsubscription
3. Verify status changed to 'unsubscribed' in DynamoDB
4. Verify no more emails are received

### Step 10: Update Documentation

Update your main README.md to reflect the new subscription features:

```bash
# Edit README.md to include:
# - Link to subscribe page
# - Information about self-service subscription
# - Updated maintenance instructions
```

## Post-Deployment Verification

### Checklist

- [ ] DynamoDB table created successfully
- [ ] API Gateway deployed and accessible
- [ ] Subscription Lambda function deployed
- [ ] Daily Lambda updated with DynamoDB integration
- [ ] Website forms uploaded to S3
- [ ] API URL configured in website JavaScript
- [ ] Existing recipients migrated to DynamoDB
- [ ] Test subscription flow completed successfully
- [ ] Test email with unsubscribe link received
- [ ] Test unsubscribe flow completed successfully
- [ ] CloudWatch logs show no errors

### Monitor CloudWatch Logs

Monitor the logs for both Lambda functions:

```bash
# Monitor Subscription Lambda
aws logs tail /aws/lambda/StoicSubscriptionHandler --follow

# Monitor Daily Sender Lambda
aws logs tail /aws/lambda/DailyStoicSender --follow
```

### Verify API Endpoints

Test the API endpoints directly:

```bash
# Test subscribe endpoint
curl -X POST "$API_URL/api/subscribe" \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com"}'

# Test confirm endpoint (with real token)
curl "$API_URL/api/confirm?token=YOUR_CONFIRMATION_TOKEN"

# Test unsubscribe endpoint
curl "$API_URL/api/unsubscribe?email=test@example.com&token=YOUR_UNSUBSCRIBE_TOKEN"
```

## Troubleshooting

### Issue: API returns 403 Forbidden

**Solution:** Check CORS configuration and ensure API Gateway has correct permissions.

```bash
# Verify API Gateway deployment
aws apigateway get-rest-apis

# Check Lambda permissions
aws lambda get-policy --function-name StoicSubscriptionHandler
```

### Issue: Confirmation emails not sending

**Solution:** Verify SES permissions and sender email verification.

```bash
# Check SES sending limits
aws ses get-send-quota

# Verify sender email
aws ses list-identities

# Check Lambda execution role
aws iam get-role --role-name StoicStack-SubscriptionHandlerRole-xxxxx
```

### Issue: DynamoDB permissions error

**Solution:** Verify Lambda has correct IAM permissions.

```bash
# Check table exists
aws dynamodb describe-table --table-name StoicSubscribers

# Verify Lambda can access table
aws lambda get-function-configuration --function-name DailyStoicSender | grep TABLE_NAME
```

### Issue: Website forms don't submit

**Solution:** Check JavaScript console for errors and verify API URL is correct.

1. Open browser developer tools (F12)
2. Check Console tab for JavaScript errors
3. Check Network tab to see API requests
4. Verify API URL is correctly configured in `subscription.js`

### Issue: Unsubscribe link doesn't work

**Solution:** Verify API_URL environment variable is set correctly.

```bash
# Check Daily Sender Lambda environment
aws lambda get-function-configuration \
  --function-name DailyStoicSender \
  --query 'Environment.Variables'
```

## Rollback Procedure

If you need to rollback the changes:

### Option 1: Keep new infrastructure, use S3 recipients

1. Update Daily Lambda to use S3 instead of DynamoDB:

```bash
aws lambda update-function-configuration \
  --function-name DailyStoicSender \
  --environment Variables={BUCKET_NAME=your-bucket,SENDER_EMAIL=reflections@jamescmooney.com,ANTHROPIC_API_KEY=your-key}
```

(Remove TABLE_NAME from environment)

2. The Lambda will automatically fallback to reading `recipients.json` from S3

### Option 2: Full rollback

```bash
# Destroy the entire stack (WARNING: This will delete DynamoDB table)
cdk destroy

# Redeploy previous version
git checkout previous-version
cdk deploy
```

## Cost Impact

The subscription features add minimal cost:

| Component | Monthly Cost |
|-----------|--------------|
| DynamoDB (on-demand) | ~$0.00 (free tier) |
| API Gateway (HTTP) | ~$0.00 (free tier) |
| Subscription Lambda | ~$0.00 (free tier) |
| **Total Additional** | **~$0.00** |

**Total service cost remains: ~$0.18/month**

## Maintenance

### Regular Tasks

1. **Monitor subscriber count:**
   ```bash
   aws dynamodb scan --table-name StoicSubscribers \
     --select COUNT \
     --filter-expression "#status = :active" \
     --expression-attribute-names '{"#status": "status"}' \
     --expression-attribute-values '{":active": {"S": "active"}}'
   ```

2. **Export subscribers (backup):**
   ```bash
   aws dynamodb scan --table-name StoicSubscribers \
     --output json > subscribers_backup_$(date +%Y%m%d).json
   ```

3. **Clean up unsubscribed records (optional):**
   - Records older than 30 days with status 'unsubscribed' can be deleted
   - Keep for GDPR compliance and to prevent re-subscription

### Updating the API

To update the subscription Lambda:

```bash
# Make changes to lambda/subscription_handler.py
# Then redeploy
cdk deploy

# Or update just the Lambda code
cd lambda
zip -r ../subscription.zip .
aws lambda update-function-code \
  --function-name StoicSubscriptionHandler \
  --zip-file fileb://../subscription.zip
```

### Updating Website Forms

```bash
# Make changes to website files
# Then sync to S3
cd website
aws s3 sync . s3://your-website-bucket/ --acl public-read
```

## Security Best Practices

1. **Restrict API CORS:** In production, update `stoic_stack.py` to restrict CORS to your domain only:
   ```python
   allow_origins=["https://jamescmooney.com"]
   ```

2. **Rate Limiting:** API Gateway automatically throttles at 10 requests/second. Adjust if needed.

3. **Token Secret:** Update the token secret in `token_manager.py`:
   - Use AWS Secrets Manager or Parameter Store
   - Change the default secret to a secure random value

4. **Monitor Abuse:** Set up CloudWatch alarms for unusual activity:
   ```bash
   # Alert on high subscription attempts
   aws cloudwatch put-metric-alarm \
     --alarm-name high-subscription-rate \
     --metric-name Invocations \
     --namespace AWS/Lambda \
     --statistic Sum \
     --period 300 \
     --threshold 100 \
     --comparison-operator GreaterThanThreshold \
     --dimensions Name=FunctionName,Value=StoicSubscriptionHandler
   ```

## Support

For issues or questions:
- Check CloudWatch Logs: `/aws/lambda/StoicSubscriptionHandler` and `/aws/lambda/DailyStoicSender`
- Review API Gateway logs in CloudWatch
- Check DynamoDB table for subscriber records
- Refer to `SUBSCRIPTION_FEATURE.md` for architecture details

## Next Steps

After successful deployment:

1. **Add Subscribe Link:** Add a prominent link to `subscribe.html` on your main website
2. **Email Signature:** Add subscription link to personal email signature
3. **Social Media:** Share the subscription page on social media
4. **Analytics:** Consider adding tracking to monitor subscription sources
5. **Welcome Email:** Consider sending a welcome email after confirmation

---

**Deployment completed!** Your Daily Stoic Reflection service now supports self-service subscription management.
