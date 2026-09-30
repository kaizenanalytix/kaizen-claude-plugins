// Copy into e2e/utils/test-data-factory.ts. Generates unique data for
// any test that creates a record, so tests can run concurrently and
// repeatedly without colliding on shared state.
export function uniqueEmail(prefix = 'user'): string {
  return `${prefix}-${crypto.randomUUID()}@example.com`;
}

export function uniqueUsername(prefix = 'user'): string {
  return `${prefix}-${crypto.randomUUID().slice(0, 8)}`;
}

export function uniqueOrderReference(): string {
  return `ORD-${crypto.randomUUID().slice(0, 8).toUpperCase()}`;
}
