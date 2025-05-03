# End-to-End Testing with Playwright

This directory contains end-to-end tests for the Mantra Demo application using Playwright.

## Setup

1. Install dependencies:
```bash
npm install
```

2. Install Playwright browsers:
```bash
npx playwright install
```

## Running Tests

### Run all E2E tests:
```bash
npm run test:e2e
```

### Run tests with UI mode:
```bash
npm run test:e2e:ui
```

### Debug tests:
```bash
npm run test:e2e:debug
```

### View test report:
```bash
npm run test:e2e:report
```

## Test Structure

- `auth.spec.ts`: Tests for authentication flows
- `workflow.spec.ts`: Tests for workflow creation and management
- `fixtures/`: Reusable test fixtures

## Best Practices

1. **Use Fixtures**: Create reusable fixtures for common operations like authentication.
2. **Mock APIs**: Use Playwright's request interception to mock API responses.
3. **Isolate Tests**: Each test should be independent and clean up after itself.
4. **Meaningful Assertions**: Write clear assertions that verify the expected behavior.
5. **Error Handling**: Test both success and error scenarios.

## CI/CD Integration

The tests are configured to run in CI/CD environments with:
- Retries enabled
- Parallel execution disabled
- Screenshots and videos on failure
- HTML report generation

## Debugging Tips

1. Use `test:e2e:debug` to run tests in debug mode
2. Check screenshots and videos in `playwright-report/` after failures
3. Use `page.pause()` to pause execution at specific points
4. Enable trace viewing with `--trace on`

## Adding New Tests

1. Create a new spec file in the `e2e/` directory
2. Use existing fixtures where applicable
3. Follow the pattern of existing tests
4. Include both positive and negative test cases
5. Add appropriate documentation 