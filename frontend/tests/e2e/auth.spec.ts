import { test, expect } from '@playwright/test';

test.describe('Authentication', () => {
  test('should display login page', async ({ page }) => {
    await page.goto('/login');

    await expect(page).toHaveTitle(/Morning Reflection/);
    await expect(page.locator('h1')).toContainText('Morning Reflection');
    await expect(page.locator('input[type="email"]')).toBeVisible();
    await expect(page.locator('input[type="password"]')).toBeVisible();
    await expect(page.locator('button[type="submit"]')).toContainText('Sign In');
  });

  test('should display validation errors for empty form', async ({ page }) => {
    await page.goto('/login');

    await page.locator('button[type="submit"]').click();

    // Should show validation errors
    await expect(page.locator('text=Email is required')).toBeVisible();
    await expect(page.locator('text=Password is required')).toBeVisible();
  });

  test('should display validation error for invalid email', async ({ page }) => {
    await page.goto('/login');

    await page.locator('input[type="email"]').fill('invalid-email');
    await page.locator('button[type="submit"]').click();

    await expect(page.locator('text=Please enter a valid email')).toBeVisible();
  });

  test('should navigate to signup page', async ({ page }) => {
    await page.goto('/login');

    await page.locator('text=Sign up').click();

    await expect(page).toHaveURL(/\/signup/);
    await expect(page.locator('h1')).toContainText('Morning Reflection');
  });

  test('should navigate to forgot password page', async ({ page }) => {
    await page.goto('/login');

    await page.locator('text=Forgot your password?').click();

    await expect(page).toHaveURL(/\/forgot-password/);
    await expect(page.locator('h1')).toContainText('Reset Password');
  });

  test('should display signup form', async ({ page }) => {
    await page.goto('/signup');

    await expect(page.locator('input[type="email"]')).toBeVisible();
    await expect(page.locator('input[type="password"]').first()).toBeVisible();
    await expect(page.locator('text=Confirm Password')).toBeVisible();
    await expect(page.locator('button[type="submit"]')).toContainText('Create Account');
  });

  test('should validate password requirements on signup', async ({ page }) => {
    await page.goto('/signup');

    await page.locator('input[type="email"]').fill('test@example.com');
    await page.locator('input[type="password"]').first().fill('weak');
    await page.locator('button[type="submit"]').click();

    // Should show password validation error
    await expect(page.locator('text=/Password must be at least 12 characters/')).toBeVisible();
  });

  test('should validate password confirmation match', async ({ page }) => {
    await page.goto('/signup');

    await page.locator('input[type="email"]').fill('test@example.com');
    await page.locator('input[type="password"]').first().fill('StrongP@ssw0rd123');
    await page.locator('input[type="password"]').nth(1).fill('DifferentP@ssw0rd');
    await page.locator('button[type="submit"]').click();

    await expect(page.locator('text=Passwords do not match')).toBeVisible();
  });
});

test.describe('Protected Routes', () => {
  test('should redirect to login when accessing dashboard without auth', async ({ page }) => {
    await page.goto('/dashboard');

    // Should redirect to login
    await expect(page).toHaveURL(/\/login/);
  });

  test('should redirect to login when accessing calendar without auth', async ({ page }) => {
    await page.goto('/calendar');

    await expect(page).toHaveURL(/\/login/);
  });

  test('should redirect to login when accessing settings without auth', async ({ page }) => {
    await page.goto('/settings');

    await expect(page).toHaveURL(/\/login/);
  });
});
