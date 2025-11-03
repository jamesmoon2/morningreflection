/**
 * AWS Amplify configuration for Cognito authentication
 *
 * This file configures AWS Amplify to work with our Cognito User Pool
 * and API Gateway backend.
 */

export const awsConfig = {
  Auth: {
    Cognito: {
      userPoolId: import.meta.env.VITE_USER_POOL_ID || '',
      userPoolClientId: import.meta.env.VITE_USER_POOL_CLIENT_ID || '',
      loginWith: {
        email: true,
      },
      signUpVerificationMethod: 'code',
      userAttributes: {
        email: {
          required: true,
        },
      },
      allowGuestAccess: false,
      passwordFormat: {
        minLength: 12,
        requireLowercase: true,
        requireUppercase: true,
        requireNumbers: true,
        requireSpecialCharacters: true,
      },
    },
  },
  API: {
    REST: {
      MorningReflectionAPI: {
        endpoint: import.meta.env.VITE_API_URL || '',
        region: import.meta.env.VITE_AWS_REGION || 'us-west-2',
      },
    },
  },
};

export const appConfig = {
  appName: import.meta.env.VITE_APP_NAME || 'Morning Reflection',
  appUrl: import.meta.env.VITE_APP_URL || 'https://app.morningreflection.com',
  awsRegion: import.meta.env.VITE_AWS_REGION || 'us-west-2',
};

/**
 * Validate that all required environment variables are set
 */
export function validateConfig(): { valid: boolean; errors: string[] } {
  const errors: string[] = [];

  if (!import.meta.env.VITE_USER_POOL_ID || import.meta.env.VITE_USER_POOL_ID === 'REPLACE_AFTER_DEPLOYMENT') {
    errors.push('VITE_USER_POOL_ID is not set or needs to be replaced');
  }

  if (!import.meta.env.VITE_USER_POOL_CLIENT_ID || import.meta.env.VITE_USER_POOL_CLIENT_ID === 'REPLACE_AFTER_DEPLOYMENT') {
    errors.push('VITE_USER_POOL_CLIENT_ID is not set or needs to be replaced');
  }

  if (!import.meta.env.VITE_API_URL || import.meta.env.VITE_API_URL === 'REPLACE_AFTER_DEPLOYMENT') {
    errors.push('VITE_API_URL is not set or needs to be replaced');
  }

  return {
    valid: errors.length === 0,
    errors,
  };
}
