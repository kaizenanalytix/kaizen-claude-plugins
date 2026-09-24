# Unit and integration tests

## Unit tests (Vitest)

Unit tests are the base of the pyramid. They test one thing — a reducer, a
hook, a utility function — with no rendering and no network mocking.

### Slice reducers

```typescript
import { productSlice, setSearchFilter } from '@/modules/products/store/productSlice';

test('setSearchFilter updates the search term', () => {
  const initial = productSlice.getInitialState();
  const next = productSlice.reducer(initial, setSearchFilter('widget'));
  expect(next.filters.search).toBe('widget');
});
```

### Custom hooks (`renderHook`)

```typescript
import { renderHook, act } from '@testing-library/react';
import { useProducts } from '@/modules/products/hooks/useProducts';
import { renderWithProviders } from '@/test/testUtils';

test('onSearch updates the search term and refilters products', () => {
  const { result } = renderHook(() => useProducts(), {
    wrapper: ({ children }) => renderWithProviders(children).container as unknown as JSX.Element,
  });
  act(() => result.current.onSearch('widget'));
  expect(result.current.search).toBe('widget');
});
```

In practice, wire `renderHook`'s `wrapper` option to the same providers
`renderWithProviders` sets up (store + query client) rather than duplicating
the setup — see `assets/testUtils.tsx`.

## Integration tests (RTL + MSW)

Integration tests render an actual component (usually a page) against a
mocked network layer, and assert on what a user would see.

```typescript
import { screen, waitFor } from '@testing-library/react';
import { setupServer } from 'msw/node';
import { http, HttpResponse } from 'msw';
import { renderWithProviders } from '@/test/testUtils';
import ProductPage from '@/modules/products/pages/ProductPage';

const server = setupServer(
  http.get('/api/v1/products', () =>
    HttpResponse.json({ items: [{ id: 1, name: 'Widget' }], total: 1 })
  )
);

beforeAll(() => server.listen());
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

test('renders the fetched product list', async () => {
  renderWithProviders(<ProductPage />);
  expect(screen.getByText(/loading/i)).toBeInTheDocument();
  await waitFor(() => expect(screen.getByText('Widget')).toBeInTheDocument());
});
```

Key points:

- MSW intercepts the real network call, so the component's actual RTK Query
  hooks run unmodified — this is testing the real data layer, not a stub.
- Use `renderWithProviders` (see `assets/testUtils.tsx`) rather than RTL's
  bare `render`, since the page needs the store, router, and query client to
  render without crashing.
- Assert on user-visible text/roles, not implementation details (e.g. don't
  assert a specific Redux action was dispatched — assert what appears on
  screen).
