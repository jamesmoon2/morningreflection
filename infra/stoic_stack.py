"""
AWS CDK Stack definition for Morning Reflection service.

Defines all AWS infrastructure: Lambda, S3, EventBridge, Secrets Manager, and IAM permissions.
"""

from aws_cdk import (
    Stack,
    Duration,
    RemovalPolicy,
    aws_lambda as lambda_,
    aws_s3 as s3,
    aws_events as events,
    aws_events_targets as targets,
    aws_iam as iam,
    aws_logs as logs,
    aws_sns as sns,
    aws_sns_subscriptions as subscriptions,
    aws_secretsmanager as secretsmanager,
    CfnOutput
)
from constructs import Construct


class StoicStack(Stack):
    """CDK Stack for Morning Reflection service."""

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Get context values from cdk.json
        anthropic_api_key = self.node.try_get_context("anthropic_api_key")
        sender_email = self.node.try_get_context("sender_email")
        s3_bucket_prefix = self.node.try_get_context("s3_bucket_prefix") or "morningreflection-prod"

        # Check if we should use Secrets Manager for API key
        use_secrets_manager = anthropic_api_key == "USE_SECRETS_MANAGER"

        if use_secrets_manager:
            print("INFO: Using AWS Secrets Manager for Anthropic API key")
        elif not anthropic_api_key or anthropic_api_key == "REPLACE_WITH_YOUR_ANTHROPIC_API_KEY":
            print("WARNING: ANTHROPIC_API_KEY not set. Set to 'USE_SECRETS_MANAGER' to use AWS Secrets Manager")

        # ===== Secrets Manager for Anthropic API Key =====
        # Create or reference the secret for Anthropic API key
        api_key_secret = None
        if use_secrets_manager:
            # Reference existing secret (must be created manually first)
            api_key_secret = secretsmanager.Secret.from_secret_name_v2(
                self, "AnthropicApiKeySecret",
                secret_name="morningreflection/anthropic-api-key"
            )

        # ===== S3 Bucket for State Management =====
        bucket = s3.Bucket(
            self, "MorningReflectionBucket",
            bucket_name=None,  # Auto-generate unique name with prefix
            versioned=True,  # Enable versioning for safety
            encryption=s3.BucketEncryption.S3_MANAGED,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            removal_policy=RemovalPolicy.RETAIN,  # Keep bucket if stack is deleted
            auto_delete_objects=False  # Don't auto-delete on stack deletion
        )

        # ===== SNS Topic for Security Alerts =====
        security_topic = sns.Topic(
            self, "SecurityAlertTopic",
            topic_name="MorningReflection-SecurityAlerts",
            display_name="Morning Reflection Security Alerts",
            fifo=False
        )

        # Get security alert email from context (optional)
        security_email = self.node.try_get_context("security_alert_email")
        if security_email:
            security_topic.add_subscription(
                subscriptions.EmailSubscription(security_email)
            )

        # ===== Lambda Function =====
        # Build environment variables
        lambda_env = {
            "BUCKET_NAME": bucket.bucket_name,
            "SENDER_EMAIL": sender_email or "reflections@morningreflection.com",
            "SECURITY_ALERT_TOPIC_ARN": security_topic.topic_arn,
        }

        # Add API key from Secrets Manager or context
        if use_secrets_manager and api_key_secret:
            lambda_env["ANTHROPIC_API_KEY_SECRET_NAME"] = "morningreflection/anthropic-api-key"
        else:
            lambda_env["ANTHROPIC_API_KEY"] = anthropic_api_key or "MISSING_API_KEY"

        lambda_fn = lambda_.Function(
            self, "MorningReflectionSender",
            function_name="MorningReflectionSender",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="handler.lambda_handler",
            code=lambda_.Code.from_asset("lambda"),
            timeout=Duration.seconds(60),
            memory_size=256,
            environment=lambda_env,
            log_retention=logs.RetentionDays.ONE_WEEK,
            description="Generates and sends daily morning reflections via email"
        )

        # Grant Lambda permissions to read/write S3 bucket
        bucket.grant_read_write(lambda_fn)

        # Grant Lambda permissions to send emails via SES
        lambda_fn.add_to_role_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "ses:SendEmail",
                    "ses:SendRawEmail"
                ],
                resources=["*"]  # SES doesn't support resource-level permissions for these actions
            )
        )

        # Grant Lambda permissions to publish to SNS topic for security alerts
        security_topic.grant_publish(lambda_fn)

        # Grant Lambda permissions to publish CloudWatch metrics
        lambda_fn.add_to_role_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "cloudwatch:PutMetricData"
                ],
                resources=["*"]  # CloudWatch metrics don't support resource-level permissions
            )
        )

        # Grant Lambda permissions to read from Secrets Manager if using it
        if use_secrets_manager and api_key_secret:
            api_key_secret.grant_read(lambda_fn)

        # ===== EventBridge Rule (Daily Trigger) =====
        # Schedule: 6 AM Pacific Time
        # PST (UTC-8): 6 AM PST = 14:00 UTC
        # PDT (UTC-7): 6 AM PDT = 13:00 UTC
        # Using 14:00 UTC for consistent 6 AM PST (will be 7 AM during PDT)
        # Adjust to 13:00 UTC if you prefer 6 AM PDT (will be 5 AM during PST)

        rule = events.Rule(
            self, "DailyTrigger",
            rule_name="MorningReflectionTrigger",
            description="Triggers daily morning reflection at 6 AM PT",
            schedule=events.Schedule.cron(
                minute="0",
                hour="14",  # 6 AM PST / 7 AM PDT
                month="*",
                week_day="*",
                year="*"
            ),
            enabled=True
        )

        # Add Lambda as target
        rule.add_target(targets.LambdaFunction(lambda_fn))

        # ===== CloudFormation Outputs =====
        CfnOutput(
            self, "BucketName",
            value=bucket.bucket_name,
            description="S3 bucket name for state files",
            export_name=f"{self.stack_name}-BucketName"
        )

        CfnOutput(
            self, "LambdaFunctionName",
            value=lambda_fn.function_name,
            description="Lambda function name",
            export_name=f"{self.stack_name}-LambdaFunctionName"
        )

        CfnOutput(
            self, "LambdaFunctionArn",
            value=lambda_fn.function_arn,
            description="Lambda function ARN",
            export_name=f"{self.stack_name}-LambdaFunctionArn"
        )

        CfnOutput(
            self, "EventRuleName",
            value=rule.rule_name,
            description="EventBridge rule name",
            export_name=f"{self.stack_name}-EventRuleName"
        )

        CfnOutput(
            self, "SecurityAlertTopicArn",
            value=security_topic.topic_arn,
            description="SNS topic ARN for security alerts",
            export_name=f"{self.stack_name}-SecurityAlertTopicArn"
        )

        CfnOutput(
            self, "SecurityAlertTopicName",
            value=security_topic.topic_name,
            description="SNS topic name for security alerts"
        )

        # Store references for potential use
        self.bucket = bucket
        self.lambda_function = lambda_fn
        self.event_rule = rule
        self.security_topic = security_topic
