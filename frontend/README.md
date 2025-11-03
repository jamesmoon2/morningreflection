# Morning Reflection - Frontend

React SPA for Morning Reflection daily wisdom and journaling application.

## Quick Start

```bash
# Install dependencies
npm install

# Copy environment template
cp .env.example .env

# Edit .env and add your AWS values (from CDK deployment)
# VITE_USER_POOL_ID, VITE_USER_POOL_CLIENT_ID, VITE_API_URL

# Start development server
npm run dev

# Open http://localhost:5173
```

## Available Scripts

- `npm run dev` - Start development server
- `npm run build` - Build for production
- `npm run preview` - Preview production build locally
- `npm run lint` - Run ESLint

## Project Structure

```
src/
├── components/     # Reusable UI components
├── pages/          # Page components (routes)
├── contexts/       # React contexts (Auth, etc.)
├── hooks/          # Custom React hooks
├── services/       # API service layer
├── types/          # TypeScript type definitions
├── utils/          # Utility functions
└── config/         # Configuration files
```

## Environment Variables

Required variables in `.env`:

- `VITE_AWS_REGION` - AWS region (e.g., us-west-2)
- `VITE_USER_POOL_ID` - Cognito User Pool ID
- `VITE_USER_POOL_CLIENT_ID` - Cognito User Pool Client ID
- `VITE_API_URL` - API Gateway URL
- `VITE_APP_NAME` - Application name
- `VITE_APP_URL` - Application URL

Get these values from CDK deployment outputs.

## Tech Stack

- **Framework**: React 18 + TypeScript
- **Build Tool**: Vite
- **Styling**: Tailwind CSS
- **Authentication**: AWS Amplify (Cognito)
- **HTTP Client**: Axios
- **Routing**: React Router v6
- **Date Utils**: date-fns

## Features

- 🔐 Email/password authentication with AWS Cognito
- 📧 Email verification and password reset flows
- 📝 Daily reflection viewing
- ✍️ Journal entry editor with word count
- 📅 Calendar view with visual indicators
- ⚙️ User settings and preferences management
- 🔗 Magic link support from emails
- 📱 Fully responsive mobile design

## Deployment

See `../Documentation/PHASE4_FRONTEND_GUIDE.md` for detailed deployment instructions.

**Quick Deploy to Amplify**:
1. Push code to Git
2. Connect repository in AWS Amplify Console
3. Set environment variables
4. Deploy!

## Development Notes

- All API calls go through centralized service layer (`src/services/`)
- Authentication state managed by `AuthContext`
- Protected routes require authentication via `ProtectedRoute` wrapper
- TypeScript strict mode enabled
- Tailwind JIT mode for fast builds

## License

Private project - All rights reserved
