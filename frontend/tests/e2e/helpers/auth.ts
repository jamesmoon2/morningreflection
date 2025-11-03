/**
 * Authentication helpers for E2E tests
 *
 * These helpers can be used to authenticate users in tests
 */

import { Page } from '@playwright/test';

export interface TestUser {
  email: string;
  password: string;
}

/**
 * Login via UI
 */
export async function loginViaUI(page: Page, user: TestUser) {
  await page.goto('/login');

  await page.locator('input[type="email"]').fill(user.email);
  await page.locator('input[type="password"]').fill(user.password);
  await page.locator('button[type="submit"]').click();

  // Wait for navigation to dashboard
  await page.waitForURL('/dashboard', { timeout: 10000 });
}

/**
 * Logout via UI
 */
export async function logoutViaUI(page: Page) {
  await page.locator('button', { hasText: 'Sign Out' }).click();

  // Wait for navigation to login
  await page.waitForURL('/login', { timeout: 5000 });
}

/**
 * Get test user credentials from environment
 */
export function getTestUser(): TestUser {
  return {
    email: process.env.TEST_USER_EMAIL || 'test@example.com',
    password: process.env.TEST_USER_PASSWORD || 'TestPassword123!',
  };
}

/**
 * Sign up a new user via UI
 */
export async function signupViaUI(page: Page, user: TestUser) {
  await page.goto('/signup');

  await page.locator('input[type="email"]').fill(user.email);
  await page.locator('input[type="password"]').first().fill(user.password);
  await page.locator('input[type="password"]').nth(1).fill(user.password);
  await page.locator('button[type="submit"]').click();

  // Wait for success or verification page
  await page.waitForURL('/verify-email', { timeout: 10000 });
}

/**
 * Verify email with code
 */
export async function verifyEmailViaUI(page: Page, email: string, code: string) {
  await page.goto('/verify-email');

  await page.locator('input[type="email"]').fill(email);
  await page.locator('input[type="text"]').fill(code);
  await page.locator('button[type="submit"]').click();

  // Wait for navigation to login
  await page.waitForURL('/login', { timeout: 10000 });
}
