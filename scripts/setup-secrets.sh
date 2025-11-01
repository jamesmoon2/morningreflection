#!/bin/bash
# Setup script for AWS Secrets Manager - Morning Reflection
# This script creates the Anthropic API key secret in AWS Secrets Manager

set -e  # Exit on error

# Configuration
SECRET_NAME="morningreflection/anthropic-api-key"
AWS_REGION="${AWS_REGION:-us-west-2}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}═══════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}  Morning Reflection - Secrets Manager Setup${NC}"
echo -e "${GREEN}═══════════════════════════════════════════════════════════${NC}"
echo

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
    echo -e "${RED}ERROR: AWS CLI is not installed.${NC}"
    echo "Please install AWS CLI: https://aws.amazon.com/cli/"
    exit 1
fi

# Check if AWS credentials are configured
if ! aws sts get-caller-identity &> /dev/null; then
    echo -e "${RED}ERROR: AWS credentials are not configured.${NC}"
    echo "Please run: aws configure"
    exit 1
fi

echo -e "${GREEN}✓${NC} AWS CLI is installed and configured"
echo

# Check if secret already exists
if aws secretsmanager describe-secret --secret-id "$SECRET_NAME" --region "$AWS_REGION" &> /dev/null; then
    echo -e "${YELLOW}WARNING: Secret '$SECRET_NAME' already exists.${NC}"
    read -p "Do you want to update it? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Aborted."
        exit 0
    fi
    UPDATE_MODE=true
else
    echo -e "Secret '$SECRET_NAME' does not exist. Creating new secret..."
    UPDATE_MODE=false
fi

# Prompt for API key
echo
echo -e "${YELLOW}Please enter your Anthropic API key:${NC}"
echo "(You can find this at: https://console.anthropic.com/settings/keys)"
read -s ANTHROPIC_API_KEY
echo

if [ -z "$ANTHROPIC_API_KEY" ]; then
    echo -e "${RED}ERROR: API key cannot be empty.${NC}"
    exit 1
fi

# Validate API key format (basic check)
if [[ ! "$ANTHROPIC_API_KEY" =~ ^sk-ant- ]]; then
    echo -e "${YELLOW}WARNING: API key doesn't match expected format (sk-ant-...).${NC}"
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Aborted."
        exit 0
    fi
fi

# Create or update the secret
echo
echo "Setting up secret in AWS Secrets Manager..."

if [ "$UPDATE_MODE" = true ]; then
    # Update existing secret
    aws secretsmanager update-secret \
        --secret-id "$SECRET_NAME" \
        --secret-string "$ANTHROPIC_API_KEY" \
        --region "$AWS_REGION" \
        > /dev/null

    echo -e "${GREEN}✓${NC} Secret updated successfully!"
else
    # Create new secret
    aws secretsmanager create-secret \
        --name "$SECRET_NAME" \
        --description "Anthropic API key for Morning Reflection service" \
        --secret-string "$ANTHROPIC_API_KEY" \
        --region "$AWS_REGION" \
        --tags Key=Project,Value=MorningReflection Key=Environment,Value=prod \
        > /dev/null

    echo -e "${GREEN}✓${NC} Secret created successfully!"
fi

echo
echo -e "${GREEN}═══════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}  Setup Complete!${NC}"
echo -e "${GREEN}═══════════════════════════════════════════════════════════${NC}"
echo
echo "Secret Name: $SECRET_NAME"
echo "AWS Region: $AWS_REGION"
echo
echo "Your Lambda function will now use this secret automatically."
echo "Make sure your Lambda execution role has permissions to read this secret."
echo

# Verify the secret can be read
echo "Verifying secret can be read..."
if aws secretsmanager get-secret-value --secret-id "$SECRET_NAME" --region "$AWS_REGION" &> /dev/null; then
    echo -e "${GREEN}✓${NC} Secret is readable!"
else
    echo -e "${RED}✗${NC} Failed to read secret. Check your IAM permissions."
    exit 1
fi

echo
echo -e "${YELLOW}Next Steps:${NC}"
echo "1. Deploy your CDK stack: cdk deploy"
echo "2. The Lambda function will automatically fetch the API key from Secrets Manager"
echo "3. Monitor CloudWatch Logs to verify the secret is being retrieved correctly"
echo

exit 0
