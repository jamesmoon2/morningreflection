#!/bin/bash
# Destroy all Morning Reflection infrastructure
# USE WITH CAUTION - This deletes all resources!

set -e

RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${RED}========================================${NC}"
echo -e "${RED}  WARNING: DESTRUCTIVE OPERATION${NC}"
echo -e "${RED}========================================${NC}"
echo ""
echo "This will DELETE all Morning Reflection infrastructure:"
echo "  - Lambda functions"
echo "  - DynamoDB tables (and ALL DATA)"
echo "  - API Gateway"
echo "  - Cognito User Pool (and ALL USERS)"
echo "  - CloudWatch dashboards and alarms"
echo "  - Amplify app (if configured)"
echo "  - S3 buckets (and ALL CONTENT)"
echo ""
echo -e "${YELLOW}This action CANNOT be undone!${NC}"
echo ""

read -p "Are you sure you want to destroy everything? (type 'yes' to confirm): " CONFIRM

if [ "$CONFIRM" != "yes" ]; then
    echo "Destruction cancelled."
    exit 0
fi

echo ""
read -p "Really? This will delete ALL user data! Type 'DELETE EVERYTHING' to confirm: " FINAL_CONFIRM

if [ "$FINAL_CONFIRM" != "DELETE EVERYTHING" ]; then
    echo "Destruction cancelled."
    exit 0
fi

echo ""
echo "Proceeding with destruction..."
echo ""

# Destroy CDK stack
echo "Destroying CDK stack..."
cdk destroy --force

if [ $? -ne 0 ]; then
    echo -e "${RED}Stack destruction failed!${NC}"
    echo "You may need to manually clean up resources."
    exit 1
fi

echo ""
echo -e "${RED}All resources destroyed.${NC}"
echo ""
echo "Note: Some resources may have a retention policy and will not be deleted:"
echo "  - S3 buckets with versioning may be retained"
echo "  - CloudWatch logs may be retained"
echo "  - Secrets Manager secrets may have a 7-30 day recovery window"
echo ""
