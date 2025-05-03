import { test, expect } from '@playwright/test';
import { test as authTest } from './fixtures/auth.fixture';

test.describe('Authentication Flow', () => {
  test('should show sign-in page when not authenticated', async ({ page }) => {
    await page.goto('/');
    await expect(page).toHaveURL('/signin');
    await expect(page.locator('h1')).toContainText('Service Connections');
    await expect(page.locator('#google-signin-btn')).toBeVisible();
  });

  test('should show Google Sign-In button', async ({ page }) => {
    await page.goto('/signin');
    const signInButton = page.locator('#google-signin-btn');
    await expect(signInButton).toBeVisible();
    await expect(signInButton).toContainText('Connect Google');
  });

  test('should handle Google auth flow', async ({ page }) => {
    // Mock the auth endpoint
    await page.route('**/api/google/auth', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          auth_url: 'http://localhost:8000/api/google/callback?code=test_code&state=test_state'
        })
      });
    });

    // Mock the callback endpoint
    await page.route('**/api/google/callback**', async route => {
      await route.fulfill({
        status: 302,
        headers: {
          'Location': '/accounts'
        }
      });
    });

    await page.goto('/signin');
    await page.click('#google-signin-btn');
    
    // Should be redirected to accounts
    await expect(page).toHaveURL('/accounts');
  });

  // Using auth fixture for authenticated tests
  authTest('should maintain authenticated state', async ({ page, signIn }) => {
    await signIn();
    
    // Navigate away and back
    await page.goto('/some-other-page');
    await page.goto('/accounts');
    
    // Should still be on accounts page
    await expect(page).toHaveURL('/accounts');
    await expect(page.locator('h1')).toContainText('Service Connections');
  });

  authTest('should handle sign out', async ({ page, signIn, signOut }) => {
    await signIn();
    await signOut();
    
    // Should be redirected to signin
    await expect(page).toHaveURL('/signin');
    
    // Try accessing accounts after signout
    await page.goto('/accounts');
    await expect(page).toHaveURL('/signin?status=Please sign in to access your account');
  });
});