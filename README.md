# MorningMeditations

Daily Stoic Reflection Email Service - Automated philosophical wisdom delivered every morning.

## Overview

An automated service that delivers daily stoic philosophical reflections via email. Each morning at 6:00 AM Pacific Time, the system uses Claude (Anthropic's AI) to select a classical stoic quote and write an original reflection, themed by month, ensuring no repeats within a year.

## Features

- **Daily Delivery**: Automated emails at 6:00 AM PT
- **AI-Generated Content**: Fresh, unique reflections using Claude Sonnet 4.5
- **Monthly Themes**: 12 distinct themes throughout the year
- **Classical Sources**: Quotes from Marcus Aurelius, Epictetus, Seneca, and Musonius Rufus
- **No Repeats**: Intelligent tracking prevents quote repetition within 365 days
- **Beautiful HTML**: Responsive email formatting optimized for all devices
- **Self-Service Subscription**: Users can subscribe and unsubscribe via web forms
- **Email Management**: Unsubscribe link in every email for easy opt-out
- **Cost-Effective**: Runs for ~$0.18/month

## Architecture

```
AWS Cloud
├── EventBridge (Daily 6 AM PT trigger)
├── Lambda Functions
│   ├── Daily Sender: Generate & send reflections
│   └── Subscription Handler: Manage subscriptions
├── DynamoDB (Subscriber management)
│   └── StoicSubscribers table
├── API Gateway (Subscription API)
│   ├── POST /api/subscribe
│   ├── GET /api/confirm
│   └── GET/POST /api/unsubscribe
├── S3 (State management)
│   ├── quote_history.json
│   └── Static website (subscription forms)
└── SES (Email delivery from jamescmooney.com)
```

## Tech Stack

- **Infrastructure**: AWS (Lambda, EventBridge, SES, S3, DynamoDB, API Gateway)
- **IaC**: AWS CDK with Python
- **Runtime**: Python 3.12
- **AI Model**: Anthropic Claude Sonnet 4.5
- **Email**: HTML via Amazon SES
- **Database**: DynamoDB for subscriber management

## Project Structure

```
daily-stoic-reflection/
├── lambda/                    # Lambda function code
│   ├── handler.py             # Daily sender entry point
│   ├── subscription_handler.py # Subscription API handler
│   ├── subscriber_manager.py  # DynamoDB operations
│   ├── token_manager.py       # Token generation/validation
│   ├── anthropic_client.py
│   ├── email_formatter.py
│   ├── quote_tracker.py
│   └── themes.py
├── infra/                     # AWS CDK infrastructure
│   └── stoic_stack.py
├── website/                   # Subscription web forms
│   ├── subscribe.html
│   ├── confirm.html
│   ├── css/
│   └── js/
├── scripts/                   # Utility scripts
│   └── migrate_subscribers.py
├── config/                    # Configuration files
│   ├── recipients.json
│   └── quote_history.json
├── tests/                     # Unit tests
└── app.py                     # CDK app entry point
```

## Setup

See [DEPLOYMENT.md](DEPLOYMENT.md) for complete setup instructions.

### Quick Start

```bash
# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure AWS credentials
aws configure

# Deploy infrastructure
cdk bootstrap  # First time only
cdk deploy
```

## Monthly Themes

1. **January**: Discipline and Self-Improvement
2. **February**: Relationships and Community
3. **March**: Resilience and Adversity
4. **April**: Nature and Acceptance
5. **May**: Virtue and Character
6. **June**: Wisdom and Philosophy
7. **July**: Freedom and Autonomy
8. **August**: Patience and Endurance
9. **September**: Purpose and Calling
10. **October**: Mortality and Impermanence
11. **November**: Gratitude and Contentment
12. **December**: Reflection and Legacy

## Subscription Management

### For Users

**Subscribe:**
Visit `https://jamescmooney.com/subscribe.html` to sign up for daily reflections.

**Unsubscribe:**
Click the unsubscribe link at the bottom of any email.

### For Administrators

See [MAINTENANCE.md](MAINTENANCE.md) for ongoing maintenance instructions.

**View Subscribers:**
```bash
aws dynamodb scan --table-name StoicSubscribers \
  --filter-expression "#status = :active" \
  --expression-attribute-names '{"#status": "status"}' \
  --expression-attribute-values '{":active": {"S": "active"}}'
```

**Manual Add:**
```bash
# Use the migration script
python scripts/migrate_subscribers.py --table StoicSubscribers
```

## Cost Breakdown

| Service | Monthly Cost |
|---------|-------------|
| Lambda | $0.00 (free tier) |
| EventBridge | $0.00 (free tier) |
| S3 | $0.00 (negligible) |
| SES | $0.003 |
| Anthropic API | $0.18 |
| **Total** | **~$0.18/month** |

## Documentation

- [prd.md](prd.md) - Complete Product Requirements Document
- [projectplan.md](projectplan.md) - Implementation Project Plan
- [DEPLOYMENT.md](DEPLOYMENT.md) - Initial Deployment Guide
- [MAINTENANCE.md](MAINTENANCE.md) - Maintenance Guide
- [ARCHITECTURE.md](ARCHITECTURE.md) - Detailed System Architecture
- [SUBSCRIPTION_FEATURE.md](SUBSCRIPTION_FEATURE.md) - Subscription Feature Design
- [SUBSCRIPTION_DEPLOYMENT.md](SUBSCRIPTION_DEPLOYMENT.md) - Subscription Deployment Guide

## License

Personal project by James Mooney