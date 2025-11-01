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
    aws_cognito as cognito,
    aws_dynamodb as dynamodb,
    aws_apigateway as apigateway,
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

        # ===== Cognito User Pool =====
        user_pool = cognito.UserPool(
            self, "MorningReflectionUserPool",
            user_pool_name="MorningReflection-Users",
            self_sign_up_enabled=True,
            sign_in_aliases=cognito.SignInAliases(
                email=True,
                username=False
            ),
            auto_verify=cognito.AutoVerifiedAttrs(email=True),
            standard_attributes=cognito.StandardAttributes(
                email=cognito.StandardAttribute(required=True, mutable=True)
            ),
            password_policy=cognito.PasswordPolicy(
                min_length=12,
                require_lowercase=True,
                require_uppercase=True,
                require_digits=True,
                require_symbols=True,
                temp_password_validity=Duration.days(3)
            ),
            mfa=cognito.Mfa.OPTIONAL,  # Users can enable 2FA
            mfa_second_factor=cognito.MfaSecondFactor(
                sms=True,
                otp=True  # TOTP (Google Authenticator, Authy)
            ),
            account_recovery=cognito.AccountRecovery.EMAIL_ONLY,
            removal_policy=RemovalPolicy.RETAIN,  # Don't delete user data if stack is deleted
            advanced_security_mode=cognito.AdvancedSecurityMode.ENFORCED,  # Compromised credentials check
            user_verification=cognito.UserVerificationConfig(
                email_subject="Verify your Morning Reflection account",
                email_body="Welcome to Morning Reflection! Please verify your email by clicking this link: {##Verify Email##}",
                email_style=cognito.VerificationEmailStyle.LINK
            )
        )

        # Create User Pool Client (for frontend application)
        user_pool_client = user_pool.add_client(
            "MorningReflectionWebClient",
            user_pool_client_name="MorningReflection-WebApp",
            auth_flows=cognito.AuthFlow(
                user_password=True,
                user_srp=True,  # Secure Remote Password
                custom=True
            ),
            access_token_validity=Duration.hours(1),
            id_token_validity=Duration.hours(1),
            refresh_token_validity=Duration.days(30),
            enable_token_revocation=True,
            prevent_user_existence_errors=True,
            generate_secret=False  # Public client (SPA)
        )

        # ===== DynamoDB Tables =====

        # Table 1: Users
        users_table = dynamodb.Table(
            self, "MorningReflectionUsersTable",
            table_name="MorningReflection-Users",
            partition_key=dynamodb.Attribute(
                name="user_id",
                type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,  # On-demand pricing
            encryption=dynamodb.TableEncryption.AWS_MANAGED,
            point_in_time_recovery=True,
            removal_policy=RemovalPolicy.RETAIN,  # Don't delete user data
            stream=dynamodb.StreamViewType.NEW_AND_OLD_IMAGES  # For audit trail
        )

        # Add GSI for email lookup
        users_table.add_global_secondary_index(
            index_name="Email-index",
            partition_key=dynamodb.Attribute(
                name="email",
                type=dynamodb.AttributeType.STRING
            ),
            projection_type=dynamodb.ProjectionType.ALL
        )

        # Table 2: Reflections
        reflections_table = dynamodb.Table(
            self, "MorningReflectionReflectionsTable",
            table_name="MorningReflection-Reflections",
            partition_key=dynamodb.Attribute(
                name="date",
                type=dynamodb.AttributeType.STRING  # YYYY-MM-DD
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            encryption=dynamodb.TableEncryption.AWS_MANAGED,
            point_in_time_recovery=True,
            removal_policy=RemovalPolicy.RETAIN
        )

        # Table 3: Journal Entries
        journal_table = dynamodb.Table(
            self, "MorningReflectionJournalTable",
            table_name="MorningReflection-JournalEntries",
            partition_key=dynamodb.Attribute(
                name="user_id",
                type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="date",
                type=dynamodb.AttributeType.STRING  # YYYY-MM-DD
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            encryption=dynamodb.TableEncryption.AWS_MANAGED,
            point_in_time_recovery=True,
            removal_policy=RemovalPolicy.RETAIN,
            stream=dynamodb.StreamViewType.NEW_AND_OLD_IMAGES  # For backups
        )

        # ===== Lambda Function (Daily Reflection Generator) =====
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

        # ===== API Lambda Functions =====

        # Shared environment variables for API Lambda functions
        api_lambda_env = {
            "DYNAMODB_USERS_TABLE": users_table.table_name,
            "DYNAMODB_REFLECTIONS_TABLE": reflections_table.table_name,
            "DYNAMODB_JOURNAL_TABLE": journal_table.table_name,
            "USER_POOL_ID": user_pool.user_pool_id,
            "USER_POOL_CLIENT_ID": user_pool_client.user_pool_client_id,
            "S3_BUCKET": bucket.bucket_name,
        }

        # Add Anthropic API key if using Secrets Manager
        if use_secrets_manager and api_key_secret:
            api_lambda_env["ANTHROPIC_API_KEY_SECRET_NAME"] = "morningreflection/anthropic-api-key"

        # Lambda function for user profile and preferences
        user_api_lambda = lambda_.Function(
            self, "UserApiFunction",
            function_name="MorningReflection-UserApi",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="user_api.lambda_handler",
            code=lambda_.Code.from_asset("lambda_api"),
            timeout=Duration.seconds(30),
            memory_size=256,
            environment=api_lambda_env,
            log_retention=logs.RetentionDays.ONE_WEEK,
            description="User profile and preferences API"
        )

        # Lambda function for reflections API
        reflections_api_lambda = lambda_.Function(
            self, "ReflectionsApiFunction",
            function_name="MorningReflection-ReflectionsApi",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="reflections_api.lambda_handler",
            code=lambda_.Code.from_asset("lambda_api"),
            timeout=Duration.seconds(30),
            memory_size=256,
            environment=api_lambda_env,
            log_retention=logs.RetentionDays.ONE_WEEK,
            description="Reflections API"
        )

        # Lambda function for journal API
        journal_api_lambda = lambda_.Function(
            self, "JournalApiFunction",
            function_name="MorningReflection-JournalApi",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="journal_api.lambda_handler",
            code=lambda_.Code.from_asset("lambda_api"),
            timeout=Duration.seconds(30),
            memory_size=512,  # More memory for journal processing
            environment=api_lambda_env,
            log_retention=logs.RetentionDays.ONE_WEEK,
            description="Journal API"
        )

        # Grant DynamoDB permissions to API Lambda functions
        users_table.grant_read_write_data(user_api_lambda)
        reflections_table.grant_read_data(reflections_api_lambda)
        reflections_table.grant_read_data(user_api_lambda)
        journal_table.grant_read_write_data(journal_api_lambda)
        users_table.grant_read_data(journal_api_lambda)

        # Grant S3 read permissions to API functions
        bucket.grant_read(user_api_lambda)
        bucket.grant_read(reflections_api_lambda)
        bucket.grant_read(journal_api_lambda)

        # Grant Secrets Manager access if needed
        if use_secrets_manager and api_key_secret:
            api_key_secret.grant_read(reflections_api_lambda)

        # ===== API Gateway =====

        # Create REST API
        api = apigateway.RestApi(
            self, "MorningReflectionApi",
            rest_api_name="MorningReflection-API",
            description="Morning Reflection REST API",
            deploy_options=apigateway.StageOptions(
                stage_name="prod",
                throttling_rate_limit=100,  # requests per second
                throttling_burst_limit=200,
                logging_level=apigateway.MethodLoggingLevel.INFO,
                data_trace_enabled=True,
                metrics_enabled=True
            ),
            default_cors_preflight_options=apigateway.CorsOptions(
                allow_origins=["*"],  # Update to specific domain in production
                allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
                allow_headers=["Content-Type", "Authorization", "X-Amz-Date", "X-Api-Key", "X-Amz-Security-Token"],
                allow_credentials=True
            )
        )

        # Create Cognito Authorizer
        authorizer = apigateway.CognitoUserPoolsAuthorizer(
            self, "MorningReflectionAuthorizer",
            cognito_user_pools=[user_pool],
            authorizer_name="MorningReflection-CognitoAuthorizer"
        )

        # API Resources and Methods

        # /user endpoint
        user_resource = api.root.add_resource("user")

        # GET /user/profile
        profile_resource = user_resource.add_resource("profile")
        profile_resource.add_method(
            "GET",
            apigateway.LambdaIntegration(user_api_lambda),
            authorizer=authorizer,
            authorization_type=apigateway.AuthorizationType.COGNITO
        )

        # PUT /user/profile
        profile_resource.add_method(
            "PUT",
            apigateway.LambdaIntegration(user_api_lambda),
            authorizer=authorizer,
            authorization_type=apigateway.AuthorizationType.COGNITO
        )

        # PUT /user/preferences
        preferences_resource = user_resource.add_resource("preferences")
        preferences_resource.add_method(
            "PUT",
            apigateway.LambdaIntegration(user_api_lambda),
            authorizer=authorizer,
            authorization_type=apigateway.AuthorizationType.COGNITO
        )

        # DELETE /user/account
        account_resource = user_resource.add_resource("account")
        account_resource.add_method(
            "DELETE",
            apigateway.LambdaIntegration(user_api_lambda),
            authorizer=authorizer,
            authorization_type=apigateway.AuthorizationType.COGNITO
        )

        # /reflections endpoint
        reflections_resource = api.root.add_resource("reflections")

        # GET /reflections/today
        today_resource = reflections_resource.add_resource("today")
        today_resource.add_method(
            "GET",
            apigateway.LambdaIntegration(reflections_api_lambda),
            authorizer=authorizer,
            authorization_type=apigateway.AuthorizationType.COGNITO
        )

        # GET /reflections/{date}
        date_resource = reflections_resource.add_resource("{date}")
        date_resource.add_method(
            "GET",
            apigateway.LambdaIntegration(reflections_api_lambda),
            authorizer=authorizer,
            authorization_type=apigateway.AuthorizationType.COGNITO
        )

        # GET /reflections/calendar
        calendar_resource = reflections_resource.add_resource("calendar")
        calendar_resource.add_method(
            "GET",
            apigateway.LambdaIntegration(reflections_api_lambda),
            authorizer=authorizer,
            authorization_type=apigateway.AuthorizationType.COGNITO
        )

        # /journal endpoint
        journal_resource = api.root.add_resource("journal")

        # POST /journal (create/update)
        journal_resource.add_method(
            "POST",
            apigateway.LambdaIntegration(journal_api_lambda),
            authorizer=authorizer,
            authorization_type=apigateway.AuthorizationType.COGNITO
        )

        # GET /journal/{date}
        journal_date_resource = journal_resource.add_resource("{date}")
        journal_date_resource.add_method(
            "GET",
            apigateway.LambdaIntegration(journal_api_lambda),
            authorizer=authorizer,
            authorization_type=apigateway.AuthorizationType.COGNITO
        )

        # DELETE /journal/{date}
        journal_date_resource.add_method(
            "DELETE",
            apigateway.LambdaIntegration(journal_api_lambda),
            authorizer=authorizer,
            authorization_type=apigateway.AuthorizationType.COGNITO
        )

        # GET /journal/list
        journal_list_resource = journal_resource.add_resource("list")
        journal_list_resource.add_method(
            "GET",
            apigateway.LambdaIntegration(journal_api_lambda),
            authorizer=authorizer,
            authorization_type=apigateway.AuthorizationType.COGNITO
        )

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

        # Cognito outputs
        CfnOutput(
            self, "UserPoolId",
            value=user_pool.user_pool_id,
            description="Cognito User Pool ID",
            export_name=f"{self.stack_name}-UserPoolId"
        )

        CfnOutput(
            self, "UserPoolClientId",
            value=user_pool_client.user_pool_client_id,
            description="Cognito User Pool Client ID",
            export_name=f"{self.stack_name}-UserPoolClientId"
        )

        CfnOutput(
            self, "UserPoolArn",
            value=user_pool.user_pool_arn,
            description="Cognito User Pool ARN"
        )

        # DynamoDB outputs
        CfnOutput(
            self, "UsersTableName",
            value=users_table.table_name,
            description="DynamoDB Users table name",
            export_name=f"{self.stack_name}-UsersTableName"
        )

        CfnOutput(
            self, "ReflectionsTableName",
            value=reflections_table.table_name,
            description="DynamoDB Reflections table name",
            export_name=f"{self.stack_name}-ReflectionsTableName"
        )

        CfnOutput(
            self, "JournalTableName",
            value=journal_table.table_name,
            description="DynamoDB Journal Entries table name",
            export_name=f"{self.stack_name}-JournalTableName"
        )

        # API Gateway outputs
        CfnOutput(
            self, "ApiUrl",
            value=api.url,
            description="API Gateway URL",
            export_name=f"{self.stack_name}-ApiUrl"
        )

        CfnOutput(
            self, "ApiId",
            value=api.rest_api_id,
            description="API Gateway REST API ID"
        )

        # Store references for potential use
        self.bucket = bucket
        self.lambda_function = lambda_fn
        self.event_rule = rule
        self.security_topic = security_topic
        self.user_pool = user_pool
        self.user_pool_client = user_pool_client
        self.users_table = users_table
        self.reflections_table = reflections_table
        self.journal_table = journal_table
        self.api = api
