import type { PropsWithChildren, ReactElement } from 'react';
import { render } from '@testing-library/react';
import type { RenderOptions } from '@testing-library/react';
import { configureStore } from '@reduxjs/toolkit';
import { Provider } from 'react-redux';
import { MemoryRouter } from 'react-router-dom';

import { productApi } from '@/modules/products/services/productApi';
import { productSlice } from '@/modules/products/store/productSlice';
// Import and spread in each additional module's reducer/middleware as the
// app grows — this file should mirror core/store/store.ts's shape, scoped
// down to what tests need.

export type AppStore = ReturnType<typeof createTestStore>;

/**
 * Builds a fresh store per test so state never leaks between tests.
 * Accepts a partial preloaded state so a test can start from a known
 * fixture (e.g. a pre-selected product, a pre-set search filter).
 */
export function createTestStore(preloadedState?: Record<string, unknown>) {
  return configureStore({
    reducer: {
      [productApi.reducerPath]: productApi.reducer,
      products: productSlice.reducer,
    },
    middleware: (getDefault) => getDefault().concat(productApi.middleware),
    preloadedState,
  });
}

interface WrapperOptions extends RenderOptions {
  preloadedState?: Record<string, unknown>;
  store?: AppStore;
  route?: string;
}

/**
 * Wraps the component under test in the same store, router, and query
 * providers the real app mounts in core/providers/AppProviders.tsx.
 * Use this instead of RTL's bare `render` for any component that reads
 * from the store, navigates, or calls an RTK Query hook.
 */
export function renderWithProviders(
  ui: ReactElement,
  { preloadedState, store = createTestStore(preloadedState), route = '/', ...renderOptions }: WrapperOptions = {}
) {
  function Wrapper({ children }: PropsWithChildren) {
    return (
      <Provider store={store}>
        <MemoryRouter initialEntries={[route]}>{children}</MemoryRouter>
      </Provider>
    );
  }

  return { store, ...render(ui, { wrapper: Wrapper, ...renderOptions }) };
}
