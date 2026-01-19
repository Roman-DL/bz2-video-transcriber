import { createContext, useContext, useState, useEffect, useCallback, type ReactNode } from 'react';
import type { ModelSettings } from '@/api/types';

const STORAGE_KEY = 'bz2-transcriber-settings';

interface SettingsContextValue {
  models: ModelSettings;
  setModels: (models: ModelSettings) => void;
  resetModels: () => void;
  isSettingsOpen: boolean;
  openSettings: () => void;
  closeSettings: () => void;
}

const SettingsContext = createContext<SettingsContextValue | null>(null);

interface SettingsProviderProps {
  children: ReactNode;
}

export function SettingsProvider({ children }: SettingsProviderProps) {
  const [models, setModelsState] = useState<ModelSettings>(() => {
    // Load from localStorage on mount
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      if (saved) {
        const parsed = JSON.parse(saved);
        return parsed.models || {};
      }
    } catch (e) {
      console.error('Failed to load settings from localStorage:', e);
    }
    return {};
  });

  const [isSettingsOpen, setIsSettingsOpen] = useState(false);

  // Save to localStorage when models change
  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify({ models }));
    } catch (e) {
      console.error('Failed to save settings to localStorage:', e);
    }
  }, [models]);

  const setModels = useCallback((newModels: ModelSettings) => {
    setModelsState(newModels);
  }, []);

  const resetModels = useCallback(() => {
    setModelsState({});
  }, []);

  const openSettings = useCallback(() => {
    setIsSettingsOpen(true);
  }, []);

  const closeSettings = useCallback(() => {
    setIsSettingsOpen(false);
  }, []);

  return (
    <SettingsContext.Provider
      value={{
        models,
        setModels,
        resetModels,
        isSettingsOpen,
        openSettings,
        closeSettings,
      }}
    >
      {children}
    </SettingsContext.Provider>
  );
}

export function useSettings() {
  const context = useContext(SettingsContext);
  if (!context) {
    throw new Error('useSettings must be used within a SettingsProvider');
  }
  return context;
}
