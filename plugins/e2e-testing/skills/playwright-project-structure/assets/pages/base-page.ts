// Copy into e2e/pages/base-page.ts. Every page object extends this.
// Keep this class limited to truly universal helpers — page-specific
// interactions belong on the subclass, not here.
import type { Page } from '@playwright/test';

export class BasePage {
  constructor(protected page: Page) {}

  async goto(path: string) {
    await this.page.goto(path);
  }
}
