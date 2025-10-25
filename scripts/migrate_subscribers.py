#!/usr/bin/env python3
"""
Migration script to import existing recipients from S3 to DynamoDB.

This script reads recipients.json from S3 and imports all email addresses
into the DynamoDB subscribers table with 'active' status.

Usage:
    python migrate_subscribers.py --bucket BUCKET_NAME --table TABLE_NAME

Or if using environment variables from CDK outputs:
    python migrate_subscribers.py
"""

import argparse
import json
import sys
import boto3
from datetime import datetime

# Add lambda directory to path for imports
sys.path.insert(0, '../lambda')
from token_manager import generate_unsubscribe_token


def load_recipients_from_s3(bucket_name: str) -> list:
    """
    Load recipients from S3 bucket.

    Args:
        bucket_name: S3 bucket name

    Returns:
        List of email addresses
    """
    s3_client = boto3.client('s3')

    try:
        response = s3_client.get_object(
            Bucket=bucket_name,
            Key='recipients.json'
        )
        content = response['Body'].read().decode('utf-8')
        config = json.loads(content)

        recipients = config.get('recipients', [])
        recipients = [r.strip() for r in recipients if r.strip()]

        print(f"✓ Loaded {len(recipients)} recipients from S3")
        return recipients

    except Exception as e:
        print(f"✗ Error loading recipients from S3: {e}")
        return []


def import_to_dynamodb(table_name: str, emails: list, dry_run: bool = False) -> dict:
    """
    Import email addresses to DynamoDB table.

    Args:
        table_name: DynamoDB table name
        emails: List of email addresses to import
        dry_run: If True, only simulate the import

    Returns:
        Dictionary with import statistics
    """
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(table_name)

    stats = {
        'total': len(emails),
        'created': 0,
        'skipped': 0,
        'failed': 0
    }

    now = datetime.utcnow().isoformat() + 'Z'

    for email in emails:
        email = email.lower().strip()

        if not email:
            continue

        print(f"\nProcessing: {email}")

        if dry_run:
            print(f"  [DRY RUN] Would import: {email}")
            stats['created'] += 1
            continue

        try:
            # Check if already exists
            response = table.get_item(Key={'email': email})

            if 'Item' in response:
                print(f"  ⊘ Skipped (already exists)")
                stats['skipped'] += 1
                continue

            # Create new subscriber
            unsubscribe_token = generate_unsubscribe_token(email)

            item = {
                'email': email,
                'status': 'active',
                'unsubscribe_token': unsubscribe_token,
                'created_at': now,
                'confirmed_at': now,
                'source': 'migration'
            }

            table.put_item(Item=item)
            print(f"  ✓ Imported successfully")
            stats['created'] += 1

        except Exception as e:
            print(f"  ✗ Failed: {e}")
            stats['failed'] += 1

    return stats


def backup_to_file(emails: list, filename: str = 'recipients_backup.json'):
    """Create a local backup of recipients."""
    backup = {
        'backup_date': datetime.utcnow().isoformat(),
        'recipients': emails
    }

    with open(filename, 'w') as f:
        json.dump(backup, f, indent=2)

    print(f"✓ Created backup file: {filename}")


def main():
    parser = argparse.ArgumentParser(
        description='Migrate email recipients from S3 to DynamoDB'
    )
    parser.add_argument(
        '--bucket',
        help='S3 bucket name (or set via AWS_S3_BUCKET env var)',
        default=None
    )
    parser.add_argument(
        '--table',
        help='DynamoDB table name (default: StoicSubscribers)',
        default='StoicSubscribers'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Simulate the migration without making changes'
    )
    parser.add_argument(
        '--no-backup',
        action='store_true',
        help='Skip creating a local backup file'
    )

    args = parser.parse_args()

    # Determine bucket name
    bucket_name = args.bucket
    if not bucket_name:
        # Try to get from CDK outputs
        try:
            cfn_client = boto3.client('cloudformation')
            response = cfn_client.describe_stacks(StackName='StoicStack')
            outputs = response['Stacks'][0]['Outputs']

            for output in outputs:
                if output['OutputKey'] == 'BucketName':
                    bucket_name = output['OutputValue']
                    break
        except Exception:
            pass

    if not bucket_name:
        print("✗ Error: Bucket name not specified and could not be determined automatically")
        print("  Use --bucket BUCKET_NAME or set AWS_S3_BUCKET environment variable")
        sys.exit(1)

    print("=" * 70)
    print("SUBSCRIBER MIGRATION SCRIPT")
    print("=" * 70)
    print(f"\nConfiguration:")
    print(f"  Source: S3 Bucket '{bucket_name}'")
    print(f"  Destination: DynamoDB Table '{args.table}'")
    print(f"  Dry Run: {'Yes' if args.dry_run else 'No'}")
    print(f"  Backup: {'No' if args.no_backup else 'Yes'}")
    print()

    if args.dry_run:
        print("⚠ DRY RUN MODE - No changes will be made\n")

    # Confirm before proceeding
    if not args.dry_run:
        response = input("Proceed with migration? (yes/no): ")
        if response.lower() != 'yes':
            print("Migration cancelled")
            sys.exit(0)

    # Load recipients from S3
    print("\n" + "=" * 70)
    print("STEP 1: Loading recipients from S3")
    print("=" * 70)

    recipients = load_recipients_from_s3(bucket_name)

    if not recipients:
        print("\n✗ No recipients found. Exiting.")
        sys.exit(1)

    print(f"\nFound {len(recipients)} recipients to migrate:")
    for email in recipients:
        print(f"  • {email}")

    # Create backup
    if not args.no_backup and not args.dry_run:
        print("\n" + "=" * 70)
        print("STEP 2: Creating backup")
        print("=" * 70)
        backup_to_file(recipients)

    # Import to DynamoDB
    print("\n" + "=" * 70)
    print(f"STEP {'3' if not args.no_backup else '2'}: Importing to DynamoDB")
    print("=" * 70)

    stats = import_to_dynamodb(args.table, recipients, dry_run=args.dry_run)

    # Print summary
    print("\n" + "=" * 70)
    print("MIGRATION SUMMARY")
    print("=" * 70)
    print(f"Total recipients: {stats['total']}")
    print(f"✓ Successfully imported: {stats['created']}")
    print(f"⊘ Skipped (already exist): {stats['skipped']}")
    print(f"✗ Failed: {stats['failed']}")
    print()

    if args.dry_run:
        print("This was a DRY RUN. No changes were made.")
        print("Run without --dry-run to perform the actual migration.")
    elif stats['failed'] == 0:
        print("✓ Migration completed successfully!")
    else:
        print("⚠ Migration completed with some failures. Please review the output above.")

    print()


if __name__ == '__main__':
    main()
