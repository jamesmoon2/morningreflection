/**
 * User API service
 *
 * Handles all user-related API operations including profile management,
 * preferences, and account operations.
 */

import { apiClient } from './api-client';
import { User, UserPreferences, ApiResponse } from '../types';

/**
 * Get current user profile
 */
export async function getUserProfile(): Promise<User> {
  return apiClient.get<User>('/user/profile');
}

/**
 * Update user profile
 */
export async function updateUserProfile(profile: Partial<User>): Promise<User> {
  return apiClient.put<User>('/user/profile', profile);
}

/**
 * Update user preferences
 */
export async function updateUserPreferences(preferences: UserPreferences): Promise<{ message: string }> {
  return apiClient.put<{ message: string }>('/user/preferences', preferences);
}

/**
 * Delete user account (GDPR-compliant)
 */
export async function deleteUserAccount(): Promise<{ message: string }> {
  return apiClient.delete<{ message: string }>('/user/account');
}

/**
 * Get user preferences
 */
export async function getUserPreferences(): Promise<UserPreferences> {
  const user = await getUserProfile();
  return user.preferences || {};
}
