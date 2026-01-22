import type { ReactNode } from 'react';
import { Header } from './Header';

interface LayoutProps {
  children: ReactNode;
}

export function Layout({ children }: LayoutProps) {
  return (
    <div className="flex flex-col h-screen bg-stone-50">
      <Header />
      <div className="flex flex-1 overflow-hidden">
        {children}
      </div>
    </div>
  );
}
