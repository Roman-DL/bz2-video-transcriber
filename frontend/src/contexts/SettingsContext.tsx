/* eslint-disable react-refresh/only-export-components */
import { createContext, useContext, useState, useEffect, useCallback, type ReactNode } from 'react';
import type { ModelSettings } from '@/api/types';

const STORAGE_KEY = 'bz2-transcriber-settings';

export type ProcessingMode = 'step' | 'auto';

interface SettingsContextValue {
  models: ModelSettings;
  setModels: (models: ModelSettings) => void;
  resetModels: () => void;
  processingMode: ProcessingMode;
  setProcessingMode: (mode: ProcessingMode) => void;
  isSettingsOpen: boolean;
  openSettings: () => void;
  closeSettings: () => void;
}

const SettingsContext = createContext<SettingsContextValue | null>(null);

interface SettingsProviderProps {
  children: ReactNode;
}

interface StoredSettings {
  models?: ModelSettings;
  processingMode?: ProcessingMode;
}

export function SettingsProvider({ children }: SettingsProviderProps) {
  const [models, setModelsState] = useState<ModelSettings>(() => {
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      if (saved) {
        const parsed: StoredSettings = JSON.parse(saved);
        return parsed.models || {};
      }
    } catch (e) {
      console.error('Failed to load settings from localStorage:', e);
    }
    return {};
  });

  const [processingMode, setProcessingModeState] = useState<ProcessingMode>(() => {
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      if (saved) {
        const parsed: StoredSettings = JSON.parse(saved);
        return parsed.processingMode || 'step';
      }
    } catch (e) {
      console.error('Failed to load settings from localStorage:', e);
    }
    return 'step';
  });

  const [isSettingsOpen, setIsSettingsOpen] = useState(false);

  // Save to localStorage when settings change
  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify({ models, processingMode }));
    } catch (e) {
      console.error('Failed to save settings to localStorage:', e);
    }
  }, [models, processingMode]);

  const setModels = useCallback((newModels: ModelSettings) => {
    setModelsState(newModels);
  }, []);

  const resetModels = useCallback(() => {
    setModelsState({});
  }, []);

  const setProcessingMode = useCallback((mode: ProcessingMode) => {
    setProcessingModeState(mode);
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
        processingMode,
        setProcessingMode,
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
