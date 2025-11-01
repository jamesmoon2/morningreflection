# Anthropic API Efficiency Architecture

## Executive Summary

**Status**: ✅ **OPTIMALLY ARCHITECTED - MINIMAL API USAGE**

The system makes **exactly 2 Anthropic API calls per day** regardless of user count:
- **1 call** for the daily reflection
- **1 call** for the journaling prompt

All users receive the same pre-generated content from DynamoDB storage.

---

## Architecture Overview

### 📅 Daily Generation Process (EventBridge Triggered)

**Trigger**: EventBridge cron schedule (once per day at 6:00 AM UTC)

**Location**: `infra/stoic_stack.py` (lines 270-293)
```python
events.Schedule.cron(
    minute='0',
    hour='6',    # 6:00 AM UTC
    day='*',
    month='*',
    year='*'
)
```

**Process Flow** (`lambda/handler.py`):

```
EventBridge (6:00 AM UTC)
    ↓
Lambda Handler Invoked (ONCE per day)
    ↓
┌─────────────────────────────────────────┐
│ 1. Load Quote from S3 Database          │ ← No API call
│    (365 pre-written quotes)              │
└─────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────┐
│ 2. Call Anthropic API #1                │ ← API CALL 1/2
│    generate_reflection_secure()          │   (lines 164-178)
│    Output: Daily reflection (~500 words) │
└─────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────┐
│ 3. Call Anthropic API #2                │ ← API CALL 2/2
│    generate_journaling_prompt()          │   (lines 204-211)
│    Output: Journaling prompt (~100 words)│
└─────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────┐
│ 4. Save to DynamoDB (ONCE)              │ ← No API call
│    Table: reflections                    │   (lines 221-230)
│    Key: date (2025-01-15)                │
│    Content:                              │
│      - quote                             │
│      - reflection                        │
│      - journaling_prompt                 │
│      - theme                             │
└─────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────┐
│ 5. Query Active Users from DynamoDB     │ ← No API call
│    (line 147)                            │
└─────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────┐
│ 6. Loop Through Users (lines 259-306)   │ ← No API calls
│    For each user:                        │
│      - Generate magic link               │
│      - Format email with SAME content    │
│      - Send via SES                      │
│                                          │
│    If 1,000 users → 1,000 emails sent    │
│    But ZERO additional API calls!        │
└─────────────────────────────────────────┘
```

---

## Web App Access (On-Demand Retrieval)

**API Endpoint**: `GET /reflections/today`

**Location**: `lambda_api/reflections_api.py` (lines 77-112)

**Process**:
```
User opens web app
    ↓
Frontend: GET /reflections/today
    ↓
Lambda: reflections_api.lambda_handler()
    ↓
┌─────────────────────────────────────────┐
│ Query DynamoDB                          │ ← No API call!
│   get_reflection_by_date(today)         │   (line 90)
│                                          │
│ Returns cached reflection from morning  │
└─────────────────────────────────────────┘
    ↓
Return to user (cached content)
```

**Key Point**: The web app **NEVER** calls Anthropic API. It **always** reads from DynamoDB.

---

## API Call Efficiency Analysis

### Scenario: 1,000 Active Users

| Event | Anthropic API Calls | DynamoDB Operations | SES Email Calls |
|-------|--------------------:|--------------------:|----------------:|
| **Morning Generation** (6:00 AM) | **2** | 1 write | 0 |
| **User Email Delivery** | **0** | 1 read (get users) | 1,000 |
| **Web App Access** (1000 users visit) | **0** | 1,000 reads | 0 |
| **Total per day** | **2** | **1,002** | **1,000** |

### Scenario: 10,000 Active Users

| Event | Anthropic API Calls | DynamoDB Operations | SES Email Calls |
|-------|--------------------:|--------------------:|----------------:|
| **Morning Generation** | **2** | 1 write | 0 |
| **User Email Delivery** | **0** | 1 read | 10,000 |
| **Web App Access** (10K users) | **0** | 10,000 reads | 0 |
| **Total per day** | **2** | **10,002** | **10,000** |

**Conclusion**: Anthropic API calls remain constant at **2 per day** regardless of user count! 🎯

---

## Cost Implications

### Anthropic API Costs (Claude Sonnet 4)

**Pricing** (as of 2025):
- Input: ~$3 per million tokens
- Output: ~$15 per million tokens

**Daily Usage Estimate**:

**API Call #1 - Reflection Generation**:
- Input: ~300 tokens (quote + theme + prompt)
- Output: ~800 tokens (reflection)
- Cost: ~$0.015 per day

**API Call #2 - Journaling Prompt**:
- Input: ~1000 tokens (reflection + quote + prompt)
- Output: ~150 tokens (journaling prompt)
- Cost: ~$0.005 per day

**Total Anthropic Cost**: ~**$0.02 per day** = ~**$7.30 per month**

**Scaling**: This cost does NOT increase with user count! ✅

---

## DynamoDB Costs

**Pricing**:
- Read: $0.25 per million requests (On-Demand)
- Write: $1.25 per million requests (On-Demand)
- Storage: $0.25 per GB-month

**Daily Usage (10,000 users)**:
- 1 write (morning generation)
- 1 read (get active users)
- 10,000 reads (web app access)
- Total: ~$0.0025 per day = ~**$0.08 per month**

**Scaling**: Linear with user count but extremely cheap.

---

## Email Delivery Timing

### Current Architecture (Single Batch)

**How it works** (`lambda/handler.py` lines 259-306):
```python
# All users get email at same time (6:00 AM UTC)
for user in users:
    send_email_via_ses(...)  # Same content to all users
```

**Characteristics**:
- ✅ Simple implementation
- ✅ All users get email simultaneously
- ✅ No per-user API calls
- ⚠️ No timezone customization
- ⚠️ Everyone gets email at 6:00 AM UTC

### User Timezone Preferences (Not Currently Implemented)

**Current DynamoDB Schema** (`lambda_api/dynamodb_operations.py`):
```python
# User table has these fields:
user = {
    'user_id': 'cognito-sub-123',
    'email': 'user@example.com',
    'timezone': 'America/Los_Angeles',     # ← Stored but not used
    'delivery_time': '08:00',              # ← Stored but not used
    'preferences': {
        'email_enabled': True
    }
}
```

**What's Stored**:
- ✅ User preferences table includes `timezone` and `delivery_time`
- ✅ Data structure supports per-user scheduling
- ❌ Lambda handler currently ignores these fields

**To Implement Timezone-Based Delivery** (Future Enhancement):

Replace the single EventBridge trigger with hourly triggers:

```python
# Instead of one trigger at 6:00 AM UTC
# Run every hour and filter users by timezone

for hour in range(24):  # 0-23
    # Get users whose local delivery_time matches current hour
    users_for_this_hour = filter_users_by_delivery_time(hour)

    # Send to users in this batch
    for user in users_for_this_hour:
        send_email_via_ses(...)
```

**Note**: Reflection/prompt still generated ONCE at start of day (6:00 AM UTC).
Only email delivery timing changes, not content generation.

---

## Architecture Benefits

### ✅ **Efficiency**
- **2 API calls per day** regardless of user count
- Scales to millions of users without additional API costs
- DynamoDB provides millisecond-latency reads

### ✅ **Consistency**
- All users see the same reflection for a given day
- No race conditions or cache inconsistency
- Single source of truth in DynamoDB

### ✅ **Reliability**
- Email delivery failure doesn't affect other users
- Web app access independent of email delivery
- Historical reflections always available

### ✅ **Cost Optimization**
- Anthropic API: ~$7/month (fixed, regardless of users)
- DynamoDB: ~$0.08/month per 10K users
- SES: ~$1/month per 10K emails
- **Total**: ~$8/month for 10K users

### ✅ **User Experience**
- Instant web app loading (cached in DynamoDB)
- Email includes magic link for one-click access
- Calendar view shows all historical reflections
- Journal entries tied to daily reflections

---

## Code References

### Generation (Daily Lambda)
- **Handler**: `lambda/handler.py:94-332`
- **API Call #1**: `lambda/handler.py:164-178` (reflection)
- **API Call #2**: `lambda/handler.py:204-211` (journaling prompt)
- **DynamoDB Save**: `lambda/handler.py:221-230`
- **Email Loop**: `lambda/handler.py:259-306`

### Retrieval (Web App API)
- **Reflections API**: `lambda_api/reflections_api.py`
- **Get Today**: `lambda_api/reflections_api.py:77-112`
- **Get by Date**: `lambda_api/reflections_api.py:115-160`
- **DynamoDB Query**: Uses `get_reflection_by_date()` - no API calls

### Infrastructure
- **EventBridge Schedule**: `infra/stoic_stack.py:270-293`
- **DynamoDB Table**: `infra/stoic_stack.py:87-134` (reflections table)

---

## Monitoring

### CloudWatch Metrics to Monitor

1. **Anthropic API Usage**:
   - Custom metric: `AnthropicAPICalls` (should be 2/day)
   - Alert if > 3 calls per day

2. **DynamoDB Performance**:
   - `ConsumedReadCapacityUnits`
   - `ConsumedWriteCapacityUnits`
   - `ThrottledRequests` (should be 0)

3. **Lambda Execution**:
   - Daily Lambda duration (should be < 30 seconds)
   - Error rate (should be 0%)

4. **Email Delivery**:
   - SES bounces
   - SES complaints
   - Delivery success rate

---

## Recommendations

### Current Architecture: ✅ **OPTIMAL**

No changes needed for API efficiency. The system is already:
- Minimizing API calls (2 per day)
- Caching aggressively (DynamoDB)
- Serving all users from cache

### Optional Future Enhancements

1. **Timezone-Based Delivery** (Phase 7+):
   - Implement hourly EventBridge triggers
   - Filter users by `delivery_time` + `timezone`
   - Still use same cached reflection (no additional API calls)

2. **CDN Caching** (High Scale):
   - Add CloudFront in front of API Gateway
   - Cache `/reflections/today` with 1-hour TTL
   - Reduces DynamoDB reads at extreme scale (100K+ users)

3. **Reflection Pre-Generation** (Optional):
   - Generate next day's reflection at 11:00 PM
   - Allows earlier error detection
   - Provides buffer for retry logic

---

## Conclusion

**✅ The architecture is ALREADY optimally designed for API efficiency.**

**Key Metrics**:
- Anthropic API calls: **2 per day** (constant, regardless of users)
- DynamoDB: Single write, multiple reads (extremely cheap)
- Cost: ~$8/month for 10,000 users
- Scalability: Linear cost scaling with users (DynamoDB/SES), but API cost remains fixed

**No changes needed** - the system is production-ready and cost-optimized! 🚀

---

**Last Updated**: 2025-11-01
**Architecture Status**: Optimal ✅
**Anthropic API Calls**: 2 per day (fixed) ✅
