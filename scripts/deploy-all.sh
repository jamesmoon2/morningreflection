#!/bin/bash
# Master deployment script for Morning Reflection
# Deploys both backend (CDK) and frontend (Amplify)

set -e

echo "=========================================="
echo "Morning Reflection - Complete Deployment"
echo "=========================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if we're in the right directory
if [ ! -f "cdk.json" ]; then
    echo -e "${RED}ERROR: Must run from project root directory${NC}"
    exit 1
fi

# Step 1: Deploy Backend
echo -e "${YELLOW}Step 1: Deploying Backend (CDK)${NC}"
echo "================================"
echo ""

echo "Running CDK deployment..."
cdk deploy --require-approval never

if [ $? -ne 0 ]; then
    echo -e "${RED}Backend deployment failed!${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Backend deployed successfully${NC}"
echo ""

# Step 2: Get CDK Outputs
echo -e "${YELLOW}Step 2: Extracting CDK Outputs${NC}"
echo "==============================="
echo ""

USER_POOL_ID=$(aws cloudformation describe-stacks \
  --stack-name MorningReflectionStack \
  --query "Stacks[0].Outputs[?OutputKey=='UserPoolId'].OutputValue" \
  --output text)

CLIENT_ID=$(aws cloudformation describe-stacks \
  --stack-name MorningReflectionStack \
  --query "Stacks[0].Outputs[?OutputKey=='UserPoolClientId'].OutputValue" \
  --output text)

API_URL=$(aws cloudformation describe-stacks \
  --stack-name MorningReflectionStack \
  --query "Stacks[0].Outputs[?OutputKey=='ApiUrl'].OutputValue" \
  --output text)

AWS_REGION=$(aws configure get region || echo "us-west-2")

echo "User Pool ID: $USER_POOL_ID"
echo "Client ID: $CLIENT_ID"
echo "API URL: $API_URL"
echo "Region: $AWS_REGION"
echo ""

# Step 3: Update Frontend Environment
echo -e "${YELLOW}Step 3: Updating Frontend Environment${NC}"
echo "======================================"
echo ""

cd frontend

# Create .env file with actual values
cat > .env <<EOF
# AWS Cognito Configuration
VITE_AWS_REGION=$AWS_REGION
VITE_USER_POOL_ID=$USER_POOL_ID
VITE_USER_POOL_CLIENT_ID=$CLIENT_ID

# API Gateway Configuration
VITE_API_URL=$API_URL

# Application Configuration
VITE_APP_NAME=Morning Reflection
VITE_APP_URL=https://app.morningreflection.com
EOF

echo -e "${GREEN}✓ Frontend environment configured${NC}"
echo ""

# Step 4: Build Frontend
echo -e "${YELLOW}Step 4: Building Frontend${NC}"
echo "========================="
echo ""

npm run build

if [ $? -ne 0 ]; then
    echo -e "${RED}Frontend build failed!${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Frontend built successfully${NC}"
echo ""

# Step 5: Deploy Frontend (if Amplify App ID exists)
echo -e "${YELLOW}Step 5: Deploying Frontend${NC}"
echo "==========================="
echo ""

AMPLIFY_APP_ID=$(aws cloudformation describe-stacks \
  --stack-name MorningReflectionStack \
  --query "Stacks[0].Outputs[?OutputKey=='AmplifyAppId'].OutputValue" \
  --output text 2>/dev/null || echo "")

if [ -n "$AMPLIFY_APP_ID" ] && [ "$AMPLIFY_APP_ID" != "None" ]; then
    echo "Triggering Amplify build for app: $AMPLIFY_APP_ID"
    aws amplify start-job \
      --app-id "$AMPLIFY_APP_ID" \
      --branch-name main \
      --job-type RELEASE

    echo -e "${GREEN}✓ Amplify deployment triggered${NC}"
    echo ""
    echo "Monitor deployment at:"
    echo "https://console.aws.amazon.com/amplify/home?region=$AWS_REGION#/$AMPLIFY_APP_ID"
else
    echo -e "${YELLOW}⚠ Amplify App ID not found. Skipping Amplify deployment.${NC}"
    echo ""
    echo "Frontend build artifacts are in frontend/dist/"
    echo ""
    echo "Manual deployment options:"
    echo "1. Deploy to S3 + CloudFront"
    echo "2. Deploy to Vercel: cd frontend && vercel --prod"
    echo "3. Deploy to Netlify: cd frontend && netlify deploy --prod --dir=dist"
fi

cd ..

# Step 6: Display Summary
echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}     Deployment Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "Backend Resources:"
echo "  - User Pool ID: $USER_POOL_ID"
echo "  - API URL: $API_URL"
echo "  - Region: $AWS_REGION"
echo ""

if [ -n "$AMPLIFY_APP_ID" ] && [ "$AMPLIFY_APP_ID" != "None" ]; then
    AMPLIFY_DOMAIN=$(aws cloudformation describe-stacks \
      --stack-name MorningReflectionStack \
      --query "Stacks[0].Outputs[?OutputKey=='AmplifyDefaultDomain'].OutputValue" \
      --output text)
    echo "Frontend URL: https://$AMPLIFY_DOMAIN"
fi

echo ""
echo "CloudWatch Dashboard:"
DASHBOARD_URL=$(aws cloudformation describe-stacks \
  --stack-name MorningReflectionStack \
  --query "Stacks[0].Outputs[?OutputKey=='DashboardUrl'].OutputValue" \
  --output text)
echo "  $DASHBOARD_URL"
echo ""

echo "Next Steps:"
echo "1. Subscribe to SNS topic for alerts"
echo "2. Configure custom domain (if not using Amplify default)"
echo "3. Test the application end-to-end"
echo "4. Set up Secrets Manager with Anthropic API key (if not done)"
echo ""
echo -e "${GREEN}All done! 🎉${NC}"
