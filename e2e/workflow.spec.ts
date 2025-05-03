import { test, expect } from '@playwright/test';
import { test as authTest } from './fixtures/auth.fixture';

test.describe('Workflow Creation', () => {
  // Setup: Sign in before each test
  test.beforeEach(async ({ page }) => {
    // Mock successful auth state
    await page.route('**/api/google/status', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          connected: true,
          user: {
            id: 'test-user-id',
            email: 'test@example.com',
            name: 'Test User'
          }
        })
      });
    });

    // Mock successful session check
    await page.route('**/api/session', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          authenticated: true,
          user: {
            id: 'test-user-id',
            email: 'test@example.com',
            name: 'Test User'
          }
        })
      });
    });

    // Set session cookie
    await page.context().addCookies([{
      name: 'session',
      value: 'test-session',
      domain: 'localhost',
      path: '/'
    }]);

    // Navigate to base URL first to set cookies
    await page.goto('http://localhost:8000');
  });

  test('should show workflow creation form', async ({ page }) => {
    await page.goto('/workflows/create');
    await expect(page.locator('h1')).toContainText('Create Workflow');
    await expect(page.getByLabel(/workflow name/i)).toBeVisible();
    await expect(page.getByLabel(/description/i)).toBeVisible();
    await expect(page.getByRole('button', { name: /create workflow/i })).toBeDisabled();
  });

  test('should enable submit button when form is valid', async ({ page }) => {
    await page.goto('/workflows/create');
    
    // Fill out form
    await page.getByLabel(/workflow name/i).fill('Test Workflow');
    await page.getByLabel(/description/i).fill('Test Description');

    // Submit button should be enabled
    const submitButton = page.getByRole('button', { name: /create workflow/i });
    await expect(submitButton).toBeEnabled();
  });

  test('should create workflow successfully', async ({ page }) => {
    // Mock workflow creation API
    await page.route('**/api/mantras/', async route => {
      const method = route.request().method();
      if (method === 'POST') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            id: 'test-workflow-id',
            name: 'Test Workflow',
            description: 'Test Description',
            status: 'active'
          })
        });
      }
    });

    await page.goto('/workflows/create');
    
    // Fill out form
    await page.getByLabel(/workflow name/i).fill('Test Workflow');
    await page.getByLabel(/description/i).fill('Test Description');

    // Submit form
    await page.getByRole('button', { name: /create workflow/i }).click();

    // Should show success message
    await expect(page.getByText(/workflow created successfully/i)).toBeVisible();

    // Should redirect to workflow list
    await expect(page).toHaveURL('/workflows');
  });

  test('should handle workflow creation error', async ({ page }) => {
    // Mock workflow creation API error
    await page.route('**/api/mantras/', async route => {
      const method = route.request().method();
      if (method === 'POST') {
        await route.fulfill({
          status: 400,
          contentType: 'application/json',
          body: JSON.stringify({
            detail: 'Invalid workflow configuration'
          })
        });
      }
    });

    await page.goto('/workflows/create');
    
    // Fill out form
    await page.getByLabel(/workflow name/i).fill('Test Workflow');
    await page.getByLabel(/description/i).fill('Test Description');

    // Submit form
    await page.getByRole('button', { name: /create workflow/i }).click();

    // Should show error message
    await expect(page.getByText(/invalid workflow configuration/i)).toBeVisible();

    // Should stay on the same page
    await expect(page).toHaveURL('/workflows/create');
  });
}); 