"""
Subscriber management module for DynamoDB operations.

Handles CRUD operations for email subscribers in the StoicSubscribers table.
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
import boto3
from botocore.exceptions import ClientError
from token_manager import generate_confirmation_token, generate_unsubscribe_token

logger = logging.getLogger()
logger.setLevel(logging.INFO)


class SubscriberManager:
    """Manages subscriber data in DynamoDB."""

    def __init__(self, table_name: str):
        """
        Initialize SubscriberManager.

        Args:
            table_name: Name of the DynamoDB table
        """
        self.table_name = table_name
        self.dynamodb = boto3.resource('dynamodb')
        self.table = self.dynamodb.Table(table_name)

    def create_subscriber(
        self,
        email: str,
        source: str = 'web'
    ) -> Dict[str, Any]:
        """
        Create a new subscriber with pending status.

        Args:
            email: Email address to subscribe
            source: Source of subscription (web, manual, migration)

        Returns:
            Dictionary with subscriber details including tokens

        Raises:
            ClientError: If DynamoDB operation fails
            ValueError: If email already exists and is active
        """
        email = email.lower().strip()

        # Check if subscriber already exists
        existing = self.get_subscriber(email)

        if existing:
            if existing['status'] == 'active':
                raise ValueError("Email is already subscribed")
            elif existing['status'] == 'pending':
                # Resend confirmation - generate new token
                return self._update_pending_subscriber(email)
            elif existing['status'] == 'unsubscribed':
                # Reactivate - generate new tokens
                return self._reactivate_subscriber(email)

        # Create new subscriber
        now = datetime.utcnow().isoformat() + 'Z'
        confirmation_token = generate_confirmation_token()
        unsubscribe_token = generate_unsubscribe_token(email)

        item = {
            'email': email,
            'status': 'pending',
            'confirmation_token': confirmation_token,
            'unsubscribe_token': unsubscribe_token,
            'created_at': now,
            'source': source
        }

        try:
            self.table.put_item(Item=item)
            logger.info(f"Created new subscriber: {email}")
            return item
        except ClientError as e:
            logger.error(f"Error creating subscriber {email}: {e}")
            raise

    def _update_pending_subscriber(self, email: str) -> Dict[str, Any]:
        """
        Update a pending subscriber with a new confirmation token.

        Args:
            email: Email address

        Returns:
            Updated subscriber item
        """
        now = datetime.utcnow().isoformat() + 'Z'
        confirmation_token = generate_confirmation_token()

        try:
            response = self.table.update_item(
                Key={'email': email},
                UpdateExpression='SET confirmation_token = :token, created_at = :now',
                ExpressionAttributeValues={
                    ':token': confirmation_token,
                    ':now': now
                },
                ReturnValues='ALL_NEW'
            )
            logger.info(f"Updated pending subscriber: {email}")
            return response['Attributes']
        except ClientError as e:
            logger.error(f"Error updating pending subscriber {email}: {e}")
            raise

    def _reactivate_subscriber(self, email: str) -> Dict[str, Any]:
        """
        Reactivate a previously unsubscribed subscriber.

        Args:
            email: Email address

        Returns:
            Updated subscriber item
        """
        now = datetime.utcnow().isoformat() + 'Z'
        confirmation_token = generate_confirmation_token()

        try:
            response = self.table.update_item(
                Key={'email': email},
                UpdateExpression='SET #status = :pending, confirmation_token = :token, '
                                'created_at = :now, confirmed_at = :null, unsubscribed_at = :null',
                ExpressionAttributeNames={
                    '#status': 'status'
                },
                ExpressionAttributeValues={
                    ':pending': 'pending',
                    ':token': confirmation_token,
                    ':now': now,
                    ':null': None
                },
                ReturnValues='ALL_NEW'
            )
            logger.info(f"Reactivated subscriber: {email}")
            return response['Attributes']
        except ClientError as e:
            logger.error(f"Error reactivating subscriber {email}: {e}")
            raise

    def confirm_subscriber(self, confirmation_token: str) -> Optional[Dict[str, Any]]:
        """
        Confirm a subscriber's email using their confirmation token.

        Args:
            confirmation_token: Token from confirmation email

        Returns:
            Updated subscriber item if found, None otherwise
        """
        # Find subscriber by confirmation token
        subscriber = self.find_by_confirmation_token(confirmation_token)

        if not subscriber:
            logger.warning(f"No subscriber found for confirmation token")
            return None

        if subscriber['status'] == 'active':
            # Already confirmed
            return subscriber

        # Update status to active
        now = datetime.utcnow().isoformat() + 'Z'
        email = subscriber['email']

        try:
            response = self.table.update_item(
                Key={'email': email},
                UpdateExpression='SET #status = :active, confirmed_at = :now, '
                                'confirmation_token = :null',
                ExpressionAttributeNames={
                    '#status': 'status'
                },
                ExpressionAttributeValues={
                    ':active': 'active',
                    ':now': now,
                    ':null': None
                },
                ReturnValues='ALL_NEW'
            )
            logger.info(f"Confirmed subscriber: {email}")
            return response['Attributes']
        except ClientError as e:
            logger.error(f"Error confirming subscriber {email}: {e}")
            raise

    def unsubscribe(self, email: str, unsubscribe_token: str) -> bool:
        """
        Unsubscribe an email address.

        Args:
            email: Email address to unsubscribe
            unsubscribe_token: Token from unsubscribe link

        Returns:
            True if successful, False if token invalid
        """
        email = email.lower().strip()

        # Get subscriber to verify token
        subscriber = self.get_subscriber(email)

        if not subscriber:
            logger.warning(f"Unsubscribe attempt for non-existent email: {email}")
            return False

        # Verify token
        if subscriber.get('unsubscribe_token') != unsubscribe_token:
            logger.warning(f"Invalid unsubscribe token for: {email}")
            return False

        # Update status to unsubscribed
        now = datetime.utcnow().isoformat() + 'Z'

        try:
            self.table.update_item(
                Key={'email': email},
                UpdateExpression='SET #status = :unsubscribed, unsubscribed_at = :now',
                ExpressionAttributeNames={
                    '#status': 'status'
                },
                ExpressionAttributeValues={
                    ':unsubscribed': 'unsubscribed',
                    ':now': now
                }
            )
            logger.info(f"Unsubscribed: {email}")
            return True
        except ClientError as e:
            logger.error(f"Error unsubscribing {email}: {e}")
            raise

    def get_subscriber(self, email: str) -> Optional[Dict[str, Any]]:
        """
        Get a subscriber by email address.

        Args:
            email: Email address to look up

        Returns:
            Subscriber item if found, None otherwise
        """
        email = email.lower().strip()

        try:
            response = self.table.get_item(Key={'email': email})
            return response.get('Item')
        except ClientError as e:
            logger.error(f"Error getting subscriber {email}: {e}")
            raise

    def find_by_confirmation_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Find a subscriber by their confirmation token.

        Args:
            token: Confirmation token to search for

        Returns:
            Subscriber item if found, None otherwise
        """
        try:
            response = self.table.scan(
                FilterExpression='confirmation_token = :token',
                ExpressionAttributeValues={':token': token}
            )

            items = response.get('Items', [])
            if items:
                return items[0]
            return None
        except ClientError as e:
            logger.error(f"Error finding subscriber by token: {e}")
            raise

    def get_active_subscribers(self) -> List[str]:
        """
        Get all active subscriber email addresses.

        Returns:
            List of email addresses with status 'active'
        """
        try:
            # If we have a GSI on status, use it for better performance
            # Otherwise, scan the table
            response = self.table.scan(
                FilterExpression='#status = :active',
                ExpressionAttributeNames={'#status': 'status'},
                ExpressionAttributeValues={':active': 'active'},
                ProjectionExpression='email'
            )

            emails = [item['email'] for item in response.get('Items', [])]

            # Handle pagination if needed
            while 'LastEvaluatedKey' in response:
                response = self.table.scan(
                    FilterExpression='#status = :active',
                    ExpressionAttributeNames={'#status': 'status'},
                    ExpressionAttributeValues={':active': 'active'},
                    ProjectionExpression='email',
                    ExclusiveStartKey=response['LastEvaluatedKey']
                )
                emails.extend([item['email'] for item in response.get('Items', [])])

            logger.info(f"Found {len(emails)} active subscribers")
            return emails

        except ClientError as e:
            logger.error(f"Error getting active subscribers: {e}")
            raise

    def get_subscriber_count_by_status(self) -> Dict[str, int]:
        """
        Get count of subscribers by status.

        Returns:
            Dictionary with counts: {pending: X, active: Y, unsubscribed: Z}
        """
        counts = {'pending': 0, 'active': 0, 'unsubscribed': 0}

        try:
            response = self.table.scan(
                ProjectionExpression='#status',
                ExpressionAttributeNames={'#status': 'status'}
            )

            for item in response.get('Items', []):
                status = item.get('status', 'unknown')
                if status in counts:
                    counts[status] += 1

            # Handle pagination
            while 'LastEvaluatedKey' in response:
                response = self.table.scan(
                    ProjectionExpression='#status',
                    ExpressionAttributeNames={'#status': 'status'},
                    ExclusiveStartKey=response['LastEvaluatedKey']
                )
                for item in response.get('Items', []):
                    status = item.get('status', 'unknown')
                    if status in counts:
                        counts[status] += 1

            logger.info(f"Subscriber counts: {counts}")
            return counts

        except ClientError as e:
            logger.error(f"Error getting subscriber counts: {e}")
            raise

    def bulk_import_subscribers(
        self,
        emails: List[str],
        source: str = 'migration',
        status: str = 'active'
    ) -> Dict[str, int]:
        """
        Bulk import subscribers (useful for migration).

        Args:
            emails: List of email addresses to import
            source: Source tag for these subscribers
            status: Status to set (default: active, for migration)

        Returns:
            Dictionary with counts: {created: X, skipped: Y, failed: Z}
        """
        results = {'created': 0, 'skipped': 0, 'failed': 0}
        now = datetime.utcnow().isoformat() + 'Z'

        for email in emails:
            email = email.lower().strip()
            if not email:
                continue

            try:
                # Check if already exists
                existing = self.get_subscriber(email)
                if existing:
                    results['skipped'] += 1
                    logger.info(f"Skipped existing subscriber: {email}")
                    continue

                # Create subscriber
                unsubscribe_token = generate_unsubscribe_token(email)
                item = {
                    'email': email,
                    'status': status,
                    'unsubscribe_token': unsubscribe_token,
                    'created_at': now,
                    'source': source
                }

                if status == 'active':
                    item['confirmed_at'] = now

                self.table.put_item(Item=item)
                results['created'] += 1
                logger.info(f"Imported subscriber: {email}")

            except Exception as e:
                results['failed'] += 1
                logger.error(f"Failed to import {email}: {e}")

        logger.info(f"Bulk import results: {results}")
        return results
