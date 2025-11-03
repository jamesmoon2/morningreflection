#!/bin/bash
# Check deployment status and health of Morning Reflection services

set -e

echo "=========================================="
echo "Morning Reflection - Deployment Status"
echo "=========================================="
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Check if stack exists
STACK_STATUS=$(aws cloudformation describe-stacks \
  --stack-name MorningReflectionStack \
  --query "Stacks[0].StackStatus" \
  --output text 2>/dev/null || echo "NOT_FOUND")

if [ "$STACK_STATUS" == "NOT_FOUND" ]; then
    echo -e "${RED}✗ Stack not deployed${NC}"
    echo ""
    echo "Run: ./scripts/deploy-all.sh"
    exit 1
fi

echo -e "${GREEN}✓ Stack Status: $STACK_STATUS${NC}"
echo ""

# Get outputs
echo "Backend Resources:"
echo "=================="

USER_POOL_ID=$(aws cloudformation describe-stacks \
  --stack-name MorningReflectionStack \
  --query "Stacks[0].Outputs[?OutputKey=='UserPoolId'].OutputValue" \
  --output text)
echo "User Pool ID: $USER_POOL_ID"

API_URL=$(aws cloudformation describe-stacks \
  --stack-name MorningReflectionStack \
  --query "Stacks[0].Outputs[?OutputKey=='ApiUrl'].OutputValue" \
  --output text)
echo "API URL: $API_URL"

LAMBDA_NAME=$(aws cloudformation describe-stacks \
  --stack-name MorningReflectionStack \
  --query "Stacks[0].Outputs[?OutputKey=='LambdaFunctionName'].OutputValue" \
  --output text)
echo "Lambda Function: $LAMBDA_NAME"

echo ""

# Check Lambda function
echo "Lambda Status:"
echo "=============="
LAMBDA_STATE=$(aws lambda get-function \
  --function-name "$LAMBDA_NAME" \
  --query "Configuration.State" \
  --output text 2>/dev/null || echo "NOT_FOUND")

if [ "$LAMBDA_STATE" == "Active" ]; then
    echo -e "${GREEN}✓ Lambda: Active${NC}"
else
    echo -e "${RED}✗ Lambda: $LAMBDA_STATE${NC}"
fi

# Get last update time
LAST_UPDATE=$(aws lambda get-function \
  --function-name "$LAMBDA_NAME" \
  --query "Configuration.LastModified" \
  --output text)
echo "Last Updated: $LAST_UPDATE"

echo ""

# Check DynamoDB tables
echo "DynamoDB Tables:"
echo "================"

USERS_TABLE=$(aws cloudformation describe-stacks \
  --stack-name MorningReflectionStack \
  --query "Stacks[0].Outputs[?OutputKey=='UsersTableName'].OutputValue" \
  --output text)
USERS_STATUS=$(aws dynamodb describe-table \
  --table-name "$USERS_TABLE" \
  --query "Table.TableStatus" \
  --output text 2>/dev/null || echo "NOT_FOUND")
echo -e "Users Table: ${GREEN}$USERS_STATUS${NC}"

REFLECTIONS_TABLE=$(aws cloudformation describe-stacks \
  --stack-name MorningReflectionStack \
  --query "Stacks[0].Outputs[?OutputKey=='ReflectionsTableName'].OutputValue" \
  --output text)
REFLECTIONS_STATUS=$(aws dynamodb describe-table \
  --table-name "$REFLECTIONS_TABLE" \
  --query "Table.TableStatus" \
  --output text 2>/dev/null || echo "NOT_FOUND")
echo -e "Reflections Table: ${GREEN}$REFLECTIONS_STATUS${NC}"

JOURNAL_TABLE=$(aws cloudformation describe-stacks \
  --stack-name MorningReflectionStack \
  --query "Stacks[0].Outputs[?OutputKey=='JournalTableName'].OutputValue" \
  --output text)
JOURNAL_STATUS=$(aws dynamodb describe-table \
  --table-name "$JOURNAL_TABLE" \
  --query "Table.TableStatus" \
  --output text 2>/dev/null || echo "NOT_FOUND")
echo -e "Journal Table: ${GREEN}$JOURNAL_STATUS${NC}"

echo ""

# Check API Gateway
echo "API Gateway:"
echo "============"
echo "Endpoint: $API_URL"

# Try to ping the API
HTTP_CODE=$(curl -o /dev/null -s -w "%{http_code}" "${API_URL}" || echo "000")
if [ "$HTTP_CODE" == "403" ] || [ "$HTTP_CODE" == "401" ]; then
    echo -e "${GREEN}✓ API Gateway: Responding (${HTTP_CODE})${NC}"
elif [ "$HTTP_CODE" == "000" ]; then
    echo -e "${RED}✗ API Gateway: Not reachable${NC}"
else
    echo -e "${YELLOW}⚠ API Gateway: HTTP ${HTTP_CODE}${NC}"
fi

echo ""

# Check Amplify (if exists)
echo "Frontend (Amplify):"
echo "==================="
AMPLIFY_APP_ID=$(aws cloudformation describe-stacks \
  --stack-name MorningReflectionStack \
  --query "Stacks[0].Outputs[?OutputKey=='AmplifyAppId'].OutputValue" \
  --output text 2>/dev/null || echo "")

if [ -n "$AMPLIFY_APP_ID" ] && [ "$AMPLIFY_APP_ID" != "None" ]; then
    AMPLIFY_STATUS=$(aws amplify get-app \
      --app-id "$AMPLIFY_APP_ID" \
      --query "app.defaultDomain" \
      --output text 2>/dev/null || echo "NOT_FOUND")
    echo -e "${GREEN}✓ Amplify App: $AMPLIFY_APP_ID${NC}"
    echo "Default Domain: https://$AMPLIFY_STATUS"

    # Check latest deployment
    LATEST_JOB=$(aws amplify list-jobs \
      --app-id "$AMPLIFY_APP_ID" \
      --branch-name main \
      --max-results 1 \
      --query "jobSummaries[0].status" \
      --output text 2>/dev/null || echo "UNKNOWN")
    echo "Latest Build: $LATEST_JOB"
else
    echo -e "${YELLOW}⚠ Amplify not configured${NC}"
fi

echo ""

# Check recent Lambda errors
echo "Recent Errors:"
echo "=============="
ERROR_COUNT=$(aws logs filter-log-events \
  --log-group-name "/aws/lambda/$LAMBDA_NAME" \
  --start-time $(($(date +%s) - 3600))000 \
  --filter-pattern "ERROR" \
  --query "length(events)" \
  --output text 2>/dev/null || echo "0")

if [ "$ERROR_COUNT" -gt 0 ]; then
    echo -e "${RED}✗ $ERROR_COUNT errors in last hour${NC}"
else
    echo -e "${GREEN}✓ No errors in last hour${NC}"
fi

echo ""

# CloudWatch Dashboard
DASHBOARD_URL=$(aws cloudformation describe-stacks \
  --stack-name MorningReflectionStack \
  --query "Stacks[0].Outputs[?OutputKey=='DashboardUrl'].OutputValue" \
  --output text)

echo "Monitoring:"
echo "==========="
echo "Dashboard: $DASHBOARD_URL"

echo ""
echo -e "${GREEN}Status check complete!${NC}"
