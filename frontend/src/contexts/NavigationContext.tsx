/* eslint-disable react-refresh/only-export-components */
import { createContext, useContext, useState, useCallback, type ReactNode } from 'react';

export type Page = 'dashboard' | 'changelog';

interface NavigationContextValue {
  page: Page;
  navigateTo: (page: Page) => void;
  goBack: () => void;
}

const NavigationContext = createContext<NavigationContextValue | null>(null);

export function NavigationProvider({ children }: { children: ReactNode }) {
  const [page, setPage] = useState<Page>('dashboard');

  const navigateTo = useCallback((target: Page) => {
    setPage(target);
  }, []);

  const goBack = useCallback(() => {
    setPage('dashboard');
  }, []);

  return (
    <NavigationContext.Provider value={{ page, navigateTo, goBack }}>
      {children}
    </NavigationContext.Provider>
  );
}

export function useNavigation() {
  const ctx = useContext(NavigationContext);
  if (!ctx) {
    throw new Error('useNavigation must be used within NavigationProvider');
  }
  return ctx;
}
