#!/usr/bin/env python3
"""
Setup script for AWS Secrets Manager - Morning Reflection
Creates the Anthropic API key secret in AWS Secrets Manager
"""

import boto3
import sys
import getpass
from botocore.exceptions import ClientError

# Configuration
SECRET_NAME = "morningreflection/anthropic-api-key"
AWS_REGION = "us-west-2"

# Colors for terminal output
class Colors:
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    RED = '\033[0;31m'
    NC = '\033[0m'  # No Color


def print_header():
    """Print the script header."""
    print(f"{Colors.GREEN}{'═' * 63}{Colors.NC}")
    print(f"{Colors.GREEN}  Morning Reflection - Secrets Manager Setup{Colors.NC}")
    print(f"{Colors.GREEN}{'═' * 63}{Colors.NC}\n")


def check_aws_credentials():
    """Verify AWS credentials are configured."""
    try:
        sts = boto3.client('sts')
        identity = sts.get_caller_identity()
        print(f"{Colors.GREEN}✓{Colors.NC} AWS credentials configured")
        print(f"  Account: {identity['Account']}")
        print(f"  User/Role: {identity['Arn']}\n")
        return True
    except Exception as e:
        print(f"{Colors.RED}ERROR: AWS credentials not configured.{Colors.NC}")
        print(f"Please run: aws configure\n")
        print(f"Error: {e}")
        return False


def secret_exists(client, secret_name):
    """Check if a secret already exists."""
    try:
        client.describe_secret(SecretId=secret_name)
        return True
    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceNotFoundException':
            return False
        raise


def get_api_key():
    """Prompt user for Anthropic API key."""
    print(f"{Colors.YELLOW}Please enter your Anthropic API key:{Colors.NC}")
    print("(You can find this at: https://console.anthropic.com/settings/keys)")

    api_key = getpass.getpass("API Key: ")

    if not api_key:
        print(f"{Colors.RED}ERROR: API key cannot be empty.{Colors.NC}")
        return None

    # Basic validation
    if not api_key.startswith('sk-ant-'):
        print(f"{Colors.YELLOW}WARNING: API key doesn't match expected format (sk-ant-...).{Colors.NC}")
        response = input("Continue anyway? (y/N): ")
        if response.lower() != 'y':
            print("Aborted.")
            return None

    return api_key


def create_secret(client, secret_name, api_key):
    """Create a new secret in Secrets Manager."""
    try:
        client.create_secret(
            Name=secret_name,
            Description="Anthropic API key for Morning Reflection service",
            SecretString=api_key,
            Tags=[
                {'Key': 'Project', 'Value': 'MorningReflection'},
                {'Key': 'Environment', 'Value': 'prod'}
            ]
        )
        print(f"{Colors.GREEN}✓{Colors.NC} Secret created successfully!")
        return True
    except ClientError as e:
        print(f"{Colors.RED}ERROR: Failed to create secret.{Colors.NC}")
        print(f"Error: {e}")
        return False


def update_secret(client, secret_name, api_key):
    """Update an existing secret in Secrets Manager."""
    try:
        client.update_secret(
            SecretId=secret_name,
            SecretString=api_key
        )
        print(f"{Colors.GREEN}✓{Colors.NC} Secret updated successfully!")
        return True
    except ClientError as e:
        print(f"{Colors.RED}ERROR: Failed to update secret.{Colors.NC}")
        print(f"Error: {e}")
        return False


def verify_secret(client, secret_name):
    """Verify the secret can be read."""
    try:
        client.get_secret_value(SecretId=secret_name)
        print(f"{Colors.GREEN}✓{Colors.NC} Secret is readable!")
        return True
    except ClientError as e:
        print(f"{Colors.RED}✗{Colors.NC} Failed to read secret. Check your IAM permissions.")
        print(f"Error: {e}")
        return False


def print_completion():
    """Print completion message with next steps."""
    print(f"\n{Colors.GREEN}{'═' * 63}{Colors.NC}")
    print(f"{Colors.GREEN}  Setup Complete!{Colors.NC}")
    print(f"{Colors.GREEN}{'═' * 63}{Colors.NC}\n")
    print(f"Secret Name: {SECRET_NAME}")
    print(f"AWS Region: {AWS_REGION}\n")
    print("Your Lambda function will now use this secret automatically.")
    print("Make sure your Lambda execution role has permissions to read this secret.\n")
    print(f"{Colors.YELLOW}Next Steps:{Colors.NC}")
    print("1. Deploy your CDK stack: cdk deploy")
    print("2. The Lambda function will automatically fetch the API key from Secrets Manager")
    print("3. Monitor CloudWatch Logs to verify the secret is being retrieved correctly\n")


def main():
    """Main function."""
    print_header()

    # Check AWS credentials
    if not check_aws_credentials():
        sys.exit(1)

    # Initialize Secrets Manager client
    client = boto3.client('secretsmanager', region_name=AWS_REGION)

    # Check if secret exists
    exists = secret_exists(client, SECRET_NAME)

    if exists:
        print(f"{Colors.YELLOW}WARNING: Secret '{SECRET_NAME}' already exists.{Colors.NC}")
        response = input("Do you want to update it? (y/N): ")
        if response.lower() != 'y':
            print("Aborted.")
            sys.exit(0)
        update_mode = True
    else:
        print(f"Secret '{SECRET_NAME}' does not exist. Creating new secret...\n")
        update_mode = False

    # Get API key from user
    api_key = get_api_key()
    if not api_key:
        sys.exit(1)

    print("\nSetting up secret in AWS Secrets Manager...")

    # Create or update the secret
    if update_mode:
        success = update_secret(client, SECRET_NAME, api_key)
    else:
        success = create_secret(client, SECRET_NAME, api_key)

    if not success:
        sys.exit(1)

    # Verify the secret
    print("\nVerifying secret can be read...")
    if not verify_secret(client, SECRET_NAME):
        sys.exit(1)

    # Print completion message
    print_completion()

    sys.exit(0)


if __name__ == "__main__":
    main()
