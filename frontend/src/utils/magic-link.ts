/**
 * Magic link utilities
 *
 * Handles parsing and validating magic link tokens from emails
 */

import { MagicLinkPayload } from '../types';

/**
 * Parse JWT token (simple base64 decode, no verification)
 * Note: Verification happens on the backend
 */
export function parseMagicLinkToken(token: string): MagicLinkPayload | null {
  try {
    // JWT format: header.payload.signature
    const parts = token.split('.');
    if (parts.length !== 3) {
      return null;
    }

    // Decode payload (middle part)
    const payload = parts[1];
    const decoded = atob(payload.replace(/-/g, '+').replace(/_/g, '/'));
    const parsed = JSON.parse(decoded) as MagicLinkPayload;

    return parsed;
  } catch (error) {
    console.error('Failed to parse magic link token:', error);
    return null;
  }
}

/**
 * Check if magic link token is expired
 */
export function isMagicLinkExpired(payload: MagicLinkPayload): boolean {
  const now = Math.floor(Date.now() / 1000);
  return payload.exp < now;
}

/**
 * Extract magic link token from URL
 */
export function extractTokenFromUrl(url: string = window.location.href): string | null {
  try {
    const urlObj = new URL(url);
    return urlObj.searchParams.get('token');
  } catch (error) {
    console.error('Failed to extract token from URL:', error);
    return null;
  }
}

/**
 * Validate magic link token
 */
export function validateMagicLink(token: string): {
  valid: boolean;
  payload: MagicLinkPayload | null;
  error?: string;
} {
  const payload = parseMagicLinkToken(token);

  if (!payload) {
    return { valid: false, payload: null, error: 'Invalid token format' };
  }

  if (isMagicLinkExpired(payload)) {
    return { valid: false, payload, error: 'Token has expired' };
  }

  return { valid: true, payload };
}
