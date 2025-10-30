"""
AWS CDK Stack definition for Daily Stoic Reflection service.

Defines all AWS infrastructure: Lambda, S3, EventBridge, and IAM permissions.
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
    CfnOutput
)
from constructs import Construct


class StoicStack(Stack):
    """CDK Stack for Daily Stoic Reflection email service."""

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Get context values from cdk.json
        anthropic_api_key = self.node.try_get_context("anthropic_api_key")
        sender_email = self.node.try_get_context("sender_email")

        if not anthropic_api_key or anthropic_api_key == "REPLACE_WITH_YOUR_ANTHROPIC_API_KEY":
            print("WARNING: ANTHROPIC_API_KEY not set in cdk.json context")

        # ===== S3 Bucket for State Management =====
        bucket = s3.Bucket(
            self, "StoicBucket",
            bucket_name=None,  # Auto-generate unique name
            versioned=True,  # Enable versioning for safety
            encryption=s3.BucketEncryption.S3_MANAGED,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            removal_policy=RemovalPolicy.RETAIN,  # Keep bucket if stack is deleted
            auto_delete_objects=False  # Don't auto-delete on stack deletion
        )

        # ===== SNS Topic for Security Alerts =====
        security_topic = sns.Topic(
            self, "SecurityAlertTopic",
            topic_name="StoicReflections-SecurityAlerts",
            display_name="Stoic Reflections Security Alerts",
            fifo=False
        )

        # Get security alert email from context (optional)
        security_email = self.node.try_get_context("security_alert_email")
        if security_email:
            security_topic.add_subscription(
                subscriptions.EmailSubscription(security_email)
            )

        # ===== Lambda Function =====
        lambda_fn = lambda_.Function(
            self, "DailyStoicSender",
            function_name="DailyStoicSender",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="handler.lambda_handler",
            code=lambda_.Code.from_asset("lambda"),
            timeout=Duration.seconds(60),
            memory_size=256,
            environment={
                "BUCKET_NAME": bucket.bucket_name,
                "SENDER_EMAIL": sender_email or "reflections@jamescmooney.com",
                "ANTHROPIC_API_KEY": anthropic_api_key or "MISSING_API_KEY",
                "SECURITY_ALERT_TOPIC_ARN": security_topic.topic_arn,
            },
            log_retention=logs.RetentionDays.ONE_WEEK,
            description="Generates and sends daily stoic reflections via email"
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

        # ===== EventBridge Rule (Daily Trigger) =====
        # Schedule: 6 AM Pacific Time
        # PST (UTC-8): 6 AM PST = 14:00 UTC
        # PDT (UTC-7): 6 AM PDT = 13:00 UTC
        # Using 14:00 UTC for consistent 6 AM PST (will be 7 AM during PDT)
        # Adjust to 13:00 UTC if you prefer 6 AM PDT (will be 5 AM during PST)

        rule = events.Rule(
            self, "DailyTrigger",
            rule_name="DailyStoicTrigger",
            description="Triggers daily stoic reflection at 6 AM PT",
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
