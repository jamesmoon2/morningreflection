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
    aws_dynamodb as dynamodb,
    aws_apigateway as apigw,
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
        website_url = self.node.try_get_context("website_url") or "https://jamescmooney.com"

        if not anthropic_api_key or anthropic_api_key == "REPLACE_WITH_YOUR_ANTHROPIC_API_KEY":
            print("WARNING: ANTHROPIC_API_KEY not set in cdk.json context")

        # ===== DynamoDB Table for Subscribers =====
        subscribers_table = dynamodb.Table(
            self, "SubscribersTable",
            table_name="StoicSubscribers",
            partition_key=dynamodb.Attribute(
                name="email",
                type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,  # On-demand pricing
            removal_policy=RemovalPolicy.RETAIN,  # Keep table if stack is deleted
            point_in_time_recovery=True,  # Enable backups
            encryption=dynamodb.TableEncryption.AWS_MANAGED
        )

        # Add GSI for querying by status
        subscribers_table.add_global_secondary_index(
            index_name="StatusIndex",
            partition_key=dynamodb.Attribute(
                name="status",
                type=dynamodb.AttributeType.STRING
            ),
            projection_type=dynamodb.ProjectionType.ALL
        )

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

        # ===== Daily Sender Lambda Function =====
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
                "TABLE_NAME": subscribers_table.table_name,
                "SENDER_EMAIL": sender_email or "reflections@jamescmooney.com",
                "ANTHROPIC_API_KEY": anthropic_api_key or "MISSING_API_KEY",
            },
            log_retention=logs.RetentionDays.ONE_WEEK,
            description="Generates and sends daily stoic reflections via email"
        )

        # Grant Lambda permissions to read/write S3 bucket
        bucket.grant_read_write(lambda_fn)

        # Grant Lambda permissions to read from DynamoDB
        subscribers_table.grant_read_data(lambda_fn)

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

        # ===== Subscription Management Lambda =====
        subscription_lambda = lambda_.Function(
            self, "SubscriptionHandler",
            function_name="StoicSubscriptionHandler",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="subscription_handler.lambda_handler",
            code=lambda_.Code.from_asset("lambda"),
            timeout=Duration.seconds(30),
            memory_size=256,
            environment={
                "TABLE_NAME": subscribers_table.table_name,
                "SENDER_EMAIL": sender_email or "reflections@jamescmooney.com",
                "WEBSITE_URL": website_url,
            },
            log_retention=logs.RetentionDays.ONE_WEEK,
            description="Handles subscription and unsubscribe requests"
        )

        # Grant subscription Lambda full access to DynamoDB table
        subscribers_table.grant_read_write_data(subscription_lambda)

        # Grant subscription Lambda permissions to send emails via SES
        subscription_lambda.add_to_role_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "ses:SendEmail",
                    "ses:SendRawEmail"
                ],
                resources=["*"]
            )
        )

        # ===== API Gateway =====
        api = apigw.RestApi(
            self, "SubscriptionApi",
            rest_api_name="Stoic Subscription API",
            description="API for managing Daily Stoic Reflection subscriptions",
            default_cors_preflight_options=apigw.CorsOptions(
                allow_origins=["*"],  # In production, restrict to your domain
                allow_methods=["GET", "POST", "OPTIONS"],
                allow_headers=["Content-Type", "Authorization"]
            )
        )

        # API resource: /api
        api_resource = api.root.add_resource("api")

        # POST /api/subscribe
        subscribe_resource = api_resource.add_resource("subscribe")
        subscribe_integration = apigw.LambdaIntegration(subscription_lambda)
        subscribe_resource.add_method("POST", subscribe_integration)

        # GET /api/confirm
        confirm_resource = api_resource.add_resource("confirm")
        confirm_integration = apigw.LambdaIntegration(subscription_lambda)
        confirm_resource.add_method("GET", confirm_integration)

        # GET/POST /api/unsubscribe
        unsubscribe_resource = api_resource.add_resource("unsubscribe")
        unsubscribe_integration = apigw.LambdaIntegration(subscription_lambda)
        unsubscribe_resource.add_method("GET", unsubscribe_integration)
        unsubscribe_resource.add_method("POST", unsubscribe_integration)

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
            self, "TableName",
            value=subscribers_table.table_name,
            description="DynamoDB table name for subscribers",
            export_name=f"{self.stack_name}-TableName"
        )

        CfnOutput(
            self, "LambdaFunctionName",
            value=lambda_fn.function_name,
            description="Daily sender Lambda function name",
            export_name=f"{self.stack_name}-LambdaFunctionName"
        )

        CfnOutput(
            self, "SubscriptionLambdaName",
            value=subscription_lambda.function_name,
            description="Subscription handler Lambda function name",
            export_name=f"{self.stack_name}-SubscriptionLambdaName"
        )

        CfnOutput(
            self, "ApiUrl",
            value=api.url,
            description="API Gateway URL",
            export_name=f"{self.stack_name}-ApiUrl"
        )

        CfnOutput(
            self, "ApiEndpoint",
            value=f"{api.url}api/",
            description="API endpoint base URL",
            export_name=f"{self.stack_name}-ApiEndpoint"
        )

        CfnOutput(
            self, "EventRuleName",
            value=rule.rule_name,
            description="EventBridge rule name",
            export_name=f"{self.stack_name}-EventRuleName"
        )

        # Store references for potential use
        self.bucket = bucket
        self.subscribers_table = subscribers_table
        self.lambda_function = lambda_fn
        self.subscription_lambda = subscription_lambda
        self.api = api
        self.event_rule = rule
