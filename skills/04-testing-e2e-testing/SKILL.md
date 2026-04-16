---
name: e2e-testing
description: E2E testing patterns with Playwright — Page Object Model, test structure, CI/CD integration, artifact management, and flaky test strategies. For Spring Boot apps, covers BDD (Cucumber) integration.
metadata:
  version: "1.1.0"
  domain: testing
  triggers: E2E testing, Playwright, end-to-end, acceptance test, browser test, Page Object Model, flaky test
  role: specialist
  scope: implementation
---

# E2E Testing Patterns

Comprehensive Playwright patterns for stable, fast, and maintainable E2E test suites.

## When to Use
- Critical user flows that must be tested as a whole
- UI behavior that unit/integration tests can't cover
- Regression testing for core workflows
- Acceptance testing after deployment

---

## Test File Organization

```
tests/
├── e2e/
│   ├── auth/
│   │   ├── login.spec.ts
│   │   ├── logout.spec.ts
│   │   └── register.spec.ts
│   ├── features/
│   │   ├── browse.spec.ts
│   │   ├── search.spec.ts
│   │   └── create.spec.ts
│   └── api/
│       └── endpoints.spec.ts
├── fixtures/
│   ├── auth.ts
│   └── data.ts
├── pages/                         ← Page Object Models
│   ├── LoginPage.ts
│   └── ItemsPage.ts
└── playwright.config.ts
```

---

## Page Object Model (POM)

```typescript
import { Page, Locator } from '@playwright/test';

export class ItemsPage {
    readonly page: Page;
    readonly searchInput: Locator;
    readonly itemCards: Locator;
    readonly createButton: Locator;

    constructor(page: Page) {
        this.page = page;
        this.searchInput = page.locator('[data-testid="search-input"]');
        this.itemCards = page.locator('[data-testid="item-card"]');
        this.createButton = page.locator('[data-testid="create-btn"]');
    }

    async goto() {
        await this.page.goto('/items');
        await this.page.waitForLoadState('networkidle');
    }

    async search(query: string) {
        await this.searchInput.fill(query);
        await this.page.waitForResponse(resp => resp.url().includes('/api/search'));
        await this.page.waitForLoadState('networkidle');
    }

    async getItemCount() {
        return await this.itemCards.count();
    }

    async createItem(name: string) {
        await this.createButton.click();
        await this.page.fill('[data-testid="name-input"]', name);
        await this.page.click('button[type="submit"]');
        await this.page.waitForSelector('[data-testid="success-message"]');
    }
}
```

---

## Test Structure

```typescript
import { test, expect } from '@playwright/test';
import { ItemsPage } from '../../pages/ItemsPage';

test.describe('Item Search', () => {
    let itemsPage: ItemsPage;

    test.beforeEach(async ({ page }) => {
        itemsPage = new ItemsPage(page);
        await itemsPage.goto();
    });

    test('returns results for valid query', async () => {
        await itemsPage.search('widget');
        expect(await itemsPage.getItemCount()).toBeGreaterThan(0);
    });

    test('shows no results for unknown query', async () => {
        await itemsPage.search('xyznonexistent');
        await expect(itemsPage.itemCards).toHaveCount(0);
    });

    test('clears results when query is cleared', async () => {
        await itemsPage.search('widget');
        await itemsPage.search('');
        // Verify all items shown again
        expect(await itemsPage.getItemCount()).toBeGreaterThan(3);
    });
});
```

---

## Playwright Configuration

```typescript
// playwright.config.ts
import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
    testDir: './tests/e2e',
    fullyParallel: true,
    retries: process.env.CI ? 2 : 0,  // Retry flaky tests in CI
    workers: process.env.CI ? 4 : undefined,
    reporter: [
        ['html', { outputFolder: 'playwright-report' }],
        ['github'],  // GitHub Actions annotations
    ],
    use: {
        baseURL: process.env.BASE_URL || 'http://localhost:3000',
        trace: 'on-first-retry',  // Capture trace on failure
        screenshot: 'only-on-failure',
        video: 'on-first-retry',
    },
    projects: [
        { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
        { name: 'firefox',  use: { ...devices['Desktop Firefox'] } },
    ],
    webServer: {
        command: 'npm run start:test',
        url: 'http://localhost:3000',
        reuseExistingServer: !process.env.CI,
    },
});
```

---

## Selectors Best Practices

```typescript
// ✅ Semantic selectors (resilient to CSS changes)
await page.click('button:has-text("Submit")');
await page.click('[data-testid="submit-button"]');
await page.click('[aria-label="Close dialog"]');
await page.fill('[name="email"]', 'test@example.com');

// ❌ Brittle selectors (break on style changes)
await page.click('.btn-primary.css-xyz123');
await page.click('div > form > button:nth-child(2)');
```

**Rule:** Add `data-testid` attributes to key interactive elements. Don't test CSS class names.

---

## Authentication Fixtures

```typescript
// fixtures/auth.ts
import { test as base } from '@playwright/test';

type AuthFixtures = {
    authenticatedPage: Page;
};

export const test = base.extend<AuthFixtures>({
    authenticatedPage: async ({ browser }, use) => {
        // Reuse saved auth state (faster than logging in each test)
        const context = await browser.newContext({
            storageState: 'playwright/.auth/user.json'
        });
        const page = await context.newPage();
        await use(page);
        await context.close();
    },
});

// auth.setup.ts — runs once before all tests
import { chromium } from '@playwright/test';

async function setup() {
    const browser = await chromium.launch();
    const page = await browser.newPage();
    
    await page.goto('/login');
    await page.fill('[name="email"]', process.env.TEST_USER_EMAIL!);
    await page.fill('[name="password"]', process.env.TEST_USER_PASSWORD!);
    await page.click('button[type="submit"]');
    await page.waitForURL('/dashboard');
    
    await page.context().storageState({ path: 'playwright/.auth/user.json' });
    await browser.close();
}

setup();
```

---

## API Mocking (For Stable Tests)

```typescript
// Mock slow or unstable external APIs
test('shows error when API fails', async ({ page }) => {
    await page.route('**/api/external-service**', route => {
        route.fulfill({ status: 503, body: 'Service Unavailable' });
    });
    
    await page.goto('/dashboard');
    await expect(page.locator('[data-testid="error-banner"]')).toBeVisible();
});

// Mock successful response
test('shows data from API', async ({ page }) => {
    await page.route('**/api/markets**', route => {
        route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify([{ id: 1, name: 'Test Market' }])
        });
    });
    
    await page.goto('/markets');
    await expect(page.locator('[data-testid="market-card"]')).toHaveCount(1);
});
```

---

## Handling Flaky Tests

```typescript
// ❌ Hard waits (flaky, slow)
await page.waitForTimeout(3000);

// ✅ Wait for specific conditions
await page.waitForSelector('[data-testid="results"]');
await page.waitForResponse(resp => resp.url().includes('/api/search') && resp.ok());
await expect(page.locator('[data-testid="loading"]')).not.toBeVisible();

// ✅ Retry assertions (Playwright auto-retries expect() by default)
await expect(page.locator('[data-testid="counter"]')).toHaveText('5');

// ✅ For animations/transitions
await page.locator('[data-testid="modal"]').waitFor({ state: 'visible' });
```

**Common causes of flaky tests:**
- Hard-coded timeouts
- Depending on external services (mock them)
- Global state between tests (use isolated contexts)
- Race conditions in UI updates (wait for specific conditions)

---

## CI/CD Integration

```yaml
# GitHub Actions
- name: Install Playwright
  run: npx playwright install --with-deps

- name: Run E2E Tests
  run: npx playwright test
  env:
    BASE_URL: http://localhost:3000
    TEST_USER_EMAIL: ${{ secrets.TEST_USER_EMAIL }}
    TEST_USER_PASSWORD: ${{ secrets.TEST_USER_PASSWORD }}

- name: Upload Playwright Report
  uses: actions/upload-artifact@v4
  if: always()
  with:
    name: playwright-report
    path: playwright-report/
    retention-days: 7
```

---

## Spring Boot: BDD with Cucumber (Alternative)

For Spring Boot microservices, BDD with Cucumber can substitute or complement Playwright:

```java
// See bdd-patterns skill for full Cucumber + Testcontainers setup
@Suite
@IncludeEngines("cucumber")
@SelectClasspathResource("features/checkout")
@ConfigurationParameter(key = GLUE_PROPERTY_NAME,
    value = "io.github.example.application.cucumber")
public class CheckoutE2ETest {}
```

---

## Best Practices

| Do | Don't |
|----|-------|
| Use `data-testid` attributes | Use CSS class selectors |
| Wait for network/DOM conditions | Use `waitForTimeout` |
| Use Page Object Model | Repeat selectors in every test |
| Mock external services | Depend on unstable third-party APIs |
| Isolate test state | Share state between tests |
| Test critical user flows | Duplicate unit test coverage |
| Run on CI with retries=2 | Skip flaky tests with `.skip` |

---

## Related Skills

- `bdd-patterns` — BDD scenarios drive E2E test scenarios; Gherkin maps to Playwright/Cypress steps
- `deployment-patterns` — E2E tests run in CI/CD pipelines as pre-production gates
- `spring-boot-testing` — E2E tests complement integration tests; unit tests sit at the base of the pyramid
- `test-driven-development` — E2E tests validate acceptance criteria; TDD drives implementation within those boundaries
- `test-quality` — E2E tests are subject to the same quality standards: one assertion, descriptive names, no magic values
