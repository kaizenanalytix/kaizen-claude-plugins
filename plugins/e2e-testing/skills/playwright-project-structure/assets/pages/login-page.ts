// Copy into e2e/pages/login-page.ts as the starting worked example for
// every other page object. Interactions only — assertions live in the spec.
import { BasePage } from './base-page';

export class LoginPage extends BasePage {
  async login(email: string, password: string) {
    await this.goto('/login');
    await this.page.getByLabel('Email').fill(email);
    await this.page.getByLabel('Password').fill(password);
    await this.page.getByRole('button', { name: 'Log in' }).click();
  }
}
