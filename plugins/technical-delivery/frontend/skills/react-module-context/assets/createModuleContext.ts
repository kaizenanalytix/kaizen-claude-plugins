import { createContext, useContext } from 'react';

/**
 * Creates a module-scoped context pair: a Provider and a typed hook that
 * throws a clear error if used outside its provider, instead of silently
 * returning null/undefined.
 *
 * Usage:
 *   const [ProductWizardProvider, useProductWizard] =
 *     createModuleContext<ProductWizardState>('ProductWizard');
 *
 * Mount the provider at the module's page boundary (e.g. wrapping the JSX
 * in pages/ProductWizardPage.tsx), never in an app-wide providers file.
 * Remember to memoize the value passed to the provider with useMemo —
 * Context has no selective re-rendering, so every consumer re-renders on
 * any value change.
 */
export function createModuleContext<T>(name: string) {
  const Ctx = createContext<T | null>(null);

  function useModuleContext(): T {
    const v = useContext(Ctx);
    if (v === null) throw new Error(`use${name} must be used within <${name}Provider>`);
    return v;
  }

  return [Ctx.Provider, useModuleContext] as const;
}
