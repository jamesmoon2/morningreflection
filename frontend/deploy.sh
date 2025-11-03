#!/bin/bash
# Frontend deployment helper script
# This script helps deploy the frontend to various hosting platforms

set -e

echo "Morning Reflection Frontend Deployment Helper"
echo "=============================================="
echo ""

# Check if .env file exists and has required values
if [ ! -f ".env" ]; then
    echo "ERROR: .env file not found!"
    echo "Please copy .env.example to .env and fill in your values."
    exit 1
fi

# Check for placeholder values
if grep -q "REPLACE_AFTER_DEPLOYMENT" .env; then
    echo "WARNING: Your .env file still contains placeholder values."
    echo "Please update the following values in .env:"
    echo "  - VITE_USER_POOL_ID"
    echo "  - VITE_USER_POOL_CLIENT_ID"
    echo "  - VITE_API_URL"
    echo ""
    echo "You can get these values by running: cdk deploy"
    exit 1
fi

# Build the frontend
echo "Building frontend..."
npm run build

echo ""
echo "Build complete! Your frontend is ready in the 'dist' directory."
echo ""
echo "Deployment Options:"
echo "==================="
echo ""
echo "1. AWS Amplify Hosting (Recommended)"
echo "   - Go to AWS Amplify Console"
echo "   - Create new app"
echo "   - Connect your Git repository"
echo "   - Point to the 'frontend' directory"
echo "   - Amplify will auto-detect the build settings"
echo ""
echo "2. AWS S3 + CloudFront"
echo "   - Create an S3 bucket for static hosting"
echo "   - Upload contents of 'dist' directory"
echo "   - Configure CloudFront distribution"
echo "   - Set up custom domain (optional)"
echo ""
echo "3. Vercel/Netlify"
echo "   - Connect your Git repository"
echo "   - Set build directory to 'frontend'"
echo "   - Set build command to 'npm run build'"
echo "   - Set output directory to 'dist'"
echo ""
echo "For detailed instructions, see: ../Documentation/PHASE4_FRONTEND_GUIDE.md"
