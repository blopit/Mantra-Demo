import { test as base } from '@playwright/test';

export type AuthFixture = {
  signIn: () => Promise<void>;
  signOut: () => Promise<void>;
};

// Extend base test with our fixture
export const test = base.extend<AuthFixture>({
  signIn: async ({ page }, use) => {
    const signIn = async () => {
      // Set up route interception for Google auth
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

      // Set up session cookie to simulate authenticated state
      await page.context().addCookies([{
        name: 'session',
        value: JSON.stringify({
          user: {
            id: 'test-user-id',
            email: 'test@example.com',
            name: 'Test User'
          }
        }),
        domain: 'localhost',
        path: '/',
      }]);

      await page.goto('/signin');
      await page.click('#google-signin-btn');
      
      // Wait for redirect to accounts
      await page.waitForURL('/accounts');
    };
    await use(signIn);
  },

  signOut: async ({ page }, use) => {
    const signOut = async () => {
      // Clear cookies and local storage
      await page.context().clearCookies();
      await page.evaluate(() => window.localStorage.clear());
      
      await page.goto('/signout');
      await page.waitForURL('/signin');
    };
    await use(signOut);
  },
}); 