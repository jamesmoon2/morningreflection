import { test, expect } from '@playwright/test';

// These tests require authentication
// You'll need to implement a login helper or use API authentication

test.describe.skip('Dashboard (Authenticated)', () => {
  test.beforeEach(async ({ page }) => {
    // TODO: Implement authentication
    // This could be done by:
    // 1. Using a test account and logging in via UI
    // 2. Setting auth tokens directly via API
    // 3. Using Playwright's storage state feature
  });

  test('should display dashboard page', async ({ page }) => {
    await page.goto('/dashboard');

    await expect(page.locator('h1')).toContainText(/\d{4}/); // Date contains year
    await expect(page.locator('text=Your daily reflection and journal')).toBeVisible();
  });

  test('should display reflection content', async ({ page }) => {
    await page.goto('/dashboard');

    // Wait for reflection to load
    await expect(page.locator('blockquote')).toBeVisible({ timeout: 10000 });
    await expect(page.locator('text=Reflection')).toBeVisible();
  });

  test('should allow journal entry', async ({ page }) => {
    await page.goto('/dashboard');

    const journalTextarea = page.locator('textarea');
    await expect(journalTextarea).toBeVisible();

    // Type in journal
    const testJournal = 'This is a test journal entry for automated testing.';
    await journalTextarea.fill(testJournal);

    // Word count should update
    await expect(page.locator('text=/\\d+ words?/')).toBeVisible();

    // Save button should be enabled
    const saveButton = page.locator('button', { hasText: 'Save Journal' });
    await expect(saveButton).toBeEnabled();
  });

  test('should navigate to calendar', async ({ page }) => {
    await page.goto('/dashboard');

    await page.locator('text=View Calendar').click();

    await expect(page).toHaveURL(/\/calendar/);
  });
});

test.describe.skip('Calendar (Authenticated)', () => {
  test.beforeEach(async ({ page }) => {
    // TODO: Implement authentication
  });

  test('should display calendar page', async ({ page }) => {
    await page.goto('/calendar');

    await expect(page.locator('h1')).toContainText('Calendar');
    await expect(page.locator('text=Browse your reflections and journal entries')).toBeVisible();
  });

  test('should display current month', async ({ page }) => {
    await page.goto('/calendar');

    const currentMonth = new Date().toLocaleDateString('en-US', { month: 'long', year: 'numeric' });
    await expect(page.locator(`text=${currentMonth}`)).toBeVisible();
  });

  test('should display day headers', async ({ page }) => {
    await page.goto('/calendar');

    await expect(page.locator('text=Sun')).toBeVisible();
    await expect(page.locator('text=Mon')).toBeVisible();
    await expect(page.locator('text=Tue')).toBeVisible();
    await expect(page.locator('text=Wed')).toBeVisible();
    await expect(page.locator('text=Thu')).toBeVisible();
    await expect(page.locator('text=Fri')).toBeVisible();
    await expect(page.locator('text=Sat')).toBeVisible();
  });

  test('should display calendar legend', async ({ page }) => {
    await page.goto('/calendar');

    await expect(page.locator('text=Legend')).toBeVisible();
    await expect(page.locator('text=Has reflection')).toBeVisible();
    await expect(page.locator('text=Has journal entry')).toBeVisible();
  });

  test('should navigate between months', async ({ page }) => {
    await page.goto('/calendar');

    const currentMonth = new Date().toLocaleDateString('en-US', { month: 'long' });

    // Click previous month
    await page.locator('button', { hasText: 'Previous' }).click();

    // Month should change
    await expect(page.locator(`text=${currentMonth}`)).not.toBeVisible();

    // Click next month
    await page.locator('button', { hasText: 'Next' }).click();

    // Should be back to current month
    await expect(page.locator(`text=${currentMonth}`)).toBeVisible();
  });
});

test.describe.skip('Settings (Authenticated)', () => {
  test.beforeEach(async ({ page }) => {
    // TODO: Implement authentication
  });

  test('should display settings page', async ({ page }) => {
    await page.goto('/settings');

    await expect(page.locator('h1')).toContainText('Settings');
    await expect(page.locator('text=Manage your account and preferences')).toBeVisible();
  });

  test('should display account information', async ({ page }) => {
    await page.goto('/settings');

    await expect(page.locator('text=Account Information')).toBeVisible();
    await expect(page.locator('text=Email')).toBeVisible();
    await expect(page.locator('text=User ID')).toBeVisible();
  });

  test('should display email preferences', async ({ page }) => {
    await page.goto('/settings');

    await expect(page.locator('text=Email Preferences')).toBeVisible();
    await expect(page.locator('text=Daily Reflection Emails')).toBeVisible();
    await expect(page.locator('text=Delivery Time')).toBeVisible();
    await expect(page.locator('text=Timezone')).toBeVisible();
  });

  test('should toggle email preference', async ({ page }) => {
    await page.goto('/settings');

    // Find the toggle button
    const toggle = page.locator('button').filter({ hasText: /Daily Reflection Emails/i });
    await toggle.click();

    // Save button should be visible
    await expect(page.locator('button', { hasText: 'Save Preferences' })).toBeVisible();
  });

  test('should display danger zone', async ({ page }) => {
    await page.goto('/settings');

    await expect(page.locator('text=Danger Zone')).toBeVisible();
    await expect(page.locator('button', { hasText: 'Delete Account' })).toBeVisible();
  });

  test('should show delete confirmation', async ({ page }) => {
    await page.goto('/settings');

    await page.locator('button', { hasText: 'Delete Account' }).click();

    await expect(page.locator('text=/Are you sure\\?/')).toBeVisible();
    await expect(page.locator('button', { hasText: 'Yes, Delete My Account' })).toBeVisible();
    await expect(page.locator('button', { hasText: 'Cancel' })).toBeVisible();
  });
});

test.describe('Navigation', () => {
  test('should display app name in header', async ({ page }) => {
    await page.goto('/login');

    await expect(page.locator('text=Morning Reflection')).toBeVisible();
  });

  test('should display footer', async ({ page }) => {
    await page.goto('/login');

    await expect(page.locator('text=/© \\d{4} Morning Reflection/')).toBeVisible();
  });
});

test.describe('Responsive Design', () => {
  test('should be mobile responsive on login page', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 }); // iPhone SE
    await page.goto('/login');

    // Form should still be visible and usable
    await expect(page.locator('input[type="email"]')).toBeVisible();
    await expect(page.locator('input[type="password"]')).toBeVisible();
    await expect(page.locator('button[type="submit"]')).toBeVisible();
  });

  test('should be mobile responsive on signup page', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 });
    await page.goto('/signup');

    await expect(page.locator('input[type="email"]')).toBeVisible();
    await expect(page.locator('input[type="password"]').first()).toBeVisible();
  });
});
