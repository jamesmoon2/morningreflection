# Recipients Migration Notice

## What Happened

The `recipients.json` file has been **removed** as part of the migration to morningreflection.com.

### Old System (Deprecated)
- Recipients were stored in `/config/recipients.json`
- Static list managed manually
- No user preferences or customization
- Example:
  ```json
  {
    "recipients": ["jamesmoon2@gmail.com"]
  }
  ```

### New System (Current)
- User data stored in **Amazon DynamoDB**
- Table name: `MorningReflection-Users`
- Supports user preferences, delivery times, timezones
- Scalable and secure

## User Data Structure (DynamoDB)

```json
{
  "user_id": "uuid-v4",
  "email": "user@example.com",
  "email_verified": true,
  "created_at": "2024-11-01T12:00:00Z",
  "preferences": {
    "delivery_time": "06:00",
    "timezone": "America/Los_Angeles",
    "email_enabled": true,
    "web_only": false
  },
  "subscription_status": "active",
  "last_login": "2024-11-01T12:00:00Z"
}
```

## For Developers

If you need to migrate the old recipient list to DynamoDB:

1. Create the DynamoDB table (see Phase 2 of MIGRATION_PLAN.md)
2. Use the AWS SDK to insert user records:

```python
import boto3
import uuid
from datetime import datetime

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('MorningReflection-Users')

# Migrate old recipient
table.put_item(
    Item={
        'user_id': str(uuid.uuid4()),
        'email': 'jamesmoon2@gmail.com',
        'email_verified': True,
        'created_at': datetime.utcnow().isoformat() + 'Z',
        'preferences': {
            'delivery_time': '06:00',
            'timezone': 'America/Los_Angeles',
            'email_enabled': True,
            'web_only': False
        },
        'subscription_status': 'active'
    }
)
```

## Phase 1 vs Phase 2

- **Phase 1** (Current): Email service uses direct recipients from handler
- **Phase 2** (Coming): Lambda will query DynamoDB for active users

---

**Last Updated**: November 1, 2024
**Migration**: Phase 1 - Domain Migration
