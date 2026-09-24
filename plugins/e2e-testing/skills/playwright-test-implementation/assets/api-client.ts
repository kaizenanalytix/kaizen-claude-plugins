// Copy into e2e/api/api-client.ts. A thin wrapper around Playwright's
// APIRequestContext for setup/teardown/verification calls made from within
// a UI test — not a general-purpose HTTP client.
//
// Construct this with the `api` fixture from fixtures/fixtures.ts (bound to
// the backend's own origin) — NOT Playwright's built-in `request` fixture,
// which resolves against the frontend's baseURL. Passing `request` here
// would silently call the frontend's own origin for what's meant to be a
// direct backend call — see references/multi-service-setup.md.
import type { APIRequestContext } from '@playwright/test';

export class ApiClient {
  constructor(private request: APIRequestContext) {}

  async createOrder(payload: { productId: string; quantity: number }) {
    const response = await this.request.post('/api/orders', { data: payload });
    return response.json();
  }

  async getOrder(orderId: string) {
    const response = await this.request.get(`/api/orders/${orderId}`);
    return response.json();
  }

  async cancelOrder(orderId: string) {
    const response = await this.request.post(`/api/orders/${orderId}/cancel`);
    return response.json();
  }
}
