/**
 * TypeScript type definitions for Morning Reflection application
 */

// ===== User Types =====

export interface User {
  user_id: string;
  email: string;
  created_at: string;
  preferences?: UserPreferences;
  profile?: UserProfile;
}

export interface UserPreferences {
  email_enabled?: boolean;
  delivery_time?: string; // HH:MM format (e.g., "07:00")
  timezone?: string; // IANA timezone (e.g., "America/New_York")
  mfa_enabled?: boolean;
}

export interface UserProfile {
  display_name?: string;
  joined_date?: string;
}

// ===== Reflection Types =====

export interface Reflection {
  date: string; // YYYY-MM-DD format
  quote: string;
  attribution: string;
  theme: string;
  reflection: string;
  journaling_prompt?: string;
  generated_at: string;
  model_version?: string;
}

// ===== Journal Types =====

export interface JournalEntry {
  user_id: string;
  date: string; // YYYY-MM-DD format
  entry: string;
  word_count: number;
  updated_at: string;
  created_at?: string;
}

export interface JournalListItem {
  date: string;
  word_count: number;
  preview: string; // First 100 characters
  updated_at: string;
}

// ===== Calendar Types =====

export interface CalendarDay {
  date: string; // YYYY-MM-DD
  hasReflection: boolean;
  hasJournal: boolean;
  wordCount?: number;
}

export interface CalendarMonth {
  year: number;
  month: number; // 1-12
  days: CalendarDay[];
}

// ===== Authentication Types =====

export interface LoginCredentials {
  email: string;
  password: string;
}

export interface SignupCredentials {
  email: string;
  password: string;
  confirmPassword: string;
}

export interface MFASetup {
  qrCodeUrl: string;
  secretCode: string;
}

export interface AuthSession {
  accessToken: string;
  idToken: string;
  refreshToken: string;
  expiresAt: number;
}

// ===== API Response Types =====

export interface ApiResponse<T> {
  success: boolean;
  data?: T;
  error?: string;
  message?: string;
}

export interface ApiError {
  statusCode: number;
  error: string;
  message: string;
}

// ===== Magic Link Types =====

export interface MagicLinkPayload {
  user_id: string;
  email: string;
  date: string;
  action: string;
  exp: number;
}

// ===== Form State Types =====

export interface FormError {
  field: string;
  message: string;
}

export interface FormState<T> {
  values: T;
  errors: FormError[];
  isSubmitting: boolean;
  isValid: boolean;
}

// ===== UI State Types =====

export interface Toast {
  id: string;
  type: 'success' | 'error' | 'info' | 'warning';
  message: string;
  duration?: number;
}

export interface LoadingState {
  isLoading: boolean;
  message?: string;
}
