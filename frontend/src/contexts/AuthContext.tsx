/**
 * Authentication Context
 *
 * Manages authentication state using AWS Cognito.
 * Provides login, logout, signup, and session management.
 */

import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { Amplify } from 'aws-amplify';
import {
  signIn,
  signUp,
  signOut,
  confirmSignUp,
  resetPassword,
  confirmResetPassword,
  getCurrentUser,
  fetchAuthSession,
  type SignInInput,
  type SignUpInput,
} from 'aws-amplify/auth';
import { awsConfig } from '../config/aws-config';
import { apiClient } from '../services/api-client';
import { User } from '../types';

// Configure Amplify
Amplify.configure(awsConfig);

interface AuthContextType {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  signup: (email: string, password: string) => Promise<void>;
  confirmSignup: (email: string, code: string) => Promise<void>;
  logout: () => Promise<void>;
  requestPasswordReset: (email: string) => Promise<void>;
  confirmPasswordReset: (email: string, code: string, newPassword: string) => Promise<void>;
  refreshSession: () => Promise<void>;
  getIdToken: () => Promise<string | null>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

interface AuthProviderProps {
  children: ReactNode;
}

export function AuthProvider({ children }: AuthProviderProps) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  /**
   * Get the current ID token from Cognito
   */
  const getIdToken = async (): Promise<string | null> => {
    try {
      const session = await fetchAuthSession();
      return session.tokens?.idToken?.toString() || null;
    } catch (error) {
      console.error('Error getting ID token:', error);
      return null;
    }
  };

  /**
   * Load current user session on mount
   */
  useEffect(() => {
    checkAuthStatus();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  /**
   * Configure API client with token getter
   */
  useEffect(() => {
    apiClient.setTokenGetter(getIdToken);
  }, []);

  /**
   * Check if user is authenticated
   */
  async function checkAuthStatus() {
    try {
      setIsLoading(true);
      const currentUser = await getCurrentUser();

      if (currentUser) {
        // Fetch user profile from our API
        await loadUserProfile();
      } else {
        setUser(null);
      }
    } catch (error) {
      console.error('Auth check failed:', error);
      setUser(null);
    } finally {
      setIsLoading(false);
    }
  }

  /**
   * Load user profile from API
   */
  async function loadUserProfile() {
    try {
      const { getUserProfile } = await import('../services/user-service');
      const profile = await getUserProfile();
      setUser(profile);
    } catch (error) {
      console.error('Failed to load user profile:', error);
      // User exists in Cognito but not in our DB yet - this is okay for new users
      setUser(null);
    }
  }

  /**
   * Sign in with email and password
   */
  async function login(email: string, password: string) {
    try {
      const signInInput: SignInInput = {
        username: email,
        password,
      };

      await signIn(signInInput);
      await loadUserProfile();
    } catch (error) {
      console.error('Login failed:', error);
      throw error;
    }
  }

  /**
   * Sign up new user
   */
  async function signup(email: string, password: string) {
    try {
      const signUpInput: SignUpInput = {
        username: email,
        password,
        options: {
          userAttributes: {
            email,
          },
        },
      };

      await signUp(signUpInput);
    } catch (error) {
      console.error('Signup failed:', error);
      throw error;
    }
  }

  /**
   * Confirm signup with verification code
   */
  async function confirmSignup(email: string, code: string) {
    try {
      await confirmSignUp({
        username: email,
        confirmationCode: code,
      });
    } catch (error) {
      console.error('Confirmation failed:', error);
      throw error;
    }
  }

  /**
   * Sign out current user
   */
  async function logout() {
    try {
      await signOut();
      setUser(null);
    } catch (error) {
      console.error('Logout failed:', error);
      throw error;
    }
  }

  /**
   * Request password reset
   */
  async function requestPasswordReset(email: string) {
    try {
      await resetPassword({ username: email });
    } catch (error) {
      console.error('Password reset request failed:', error);
      throw error;
    }
  }

  /**
   * Confirm password reset with code
   */
  async function confirmPasswordReset(email: string, code: string, newPassword: string) {
    try {
      await confirmResetPassword({
        username: email,
        confirmationCode: code,
        newPassword,
      });
    } catch (error) {
      console.error('Password reset confirmation failed:', error);
      throw error;
    }
  }

  /**
   * Refresh the current session
   */
  async function refreshSession() {
    await checkAuthStatus();
  }

  const value: AuthContextType = {
    user,
    isAuthenticated: !!user,
    isLoading,
    login,
    signup,
    confirmSignup,
    logout,
    requestPasswordReset,
    confirmPasswordReset,
    refreshSession,
    getIdToken,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

/**
 * Hook to use auth context
 */
export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
