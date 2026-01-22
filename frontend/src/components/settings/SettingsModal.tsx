import { useState, useEffect, useMemo } from 'react';
import { Button } from '@/components/common/Button';
import { Spinner } from '@/components/common/Spinner';
import { ModelSelector } from '@/components/settings/ModelSelector';
import { useSettings } from '@/contexts/SettingsContext';
import { useAvailableModels, useDefaultModels, useModelsConfig } from '@/api/hooks/useModels';
import { whisperToOptions, buildLLMOptions } from '@/utils/modelUtils';
import type { ModelSettings, ModelConfig } from '@/api/types';
import { RotateCcw, X } from 'lucide-react';

type PipelineStage = 'transcribe' | 'clean' | 'longread' | 'summarize';

export function SettingsModal() {
  const { models, setModels, isSettingsOpen, closeSettings } = useSettings();
  const { data: availableModels, isLoading: isLoadingAvailable } = useAvailableModels();
  const { data: defaultModels, isLoading: isLoadingDefault } = useDefaultModels();
  const { data: modelsConfig, isLoading: isLoadingConfig } = useModelsConfig();

  // Local state for editing
  const [localModels, setLocalModels] = useState<ModelSettings>({});

  // Reset local state when modal opens
  useEffect(() => {
    if (isSettingsOpen) {
      setLocalModels(models);
    }
  }, [isSettingsOpen, models]);

  const isLoading = isLoadingAvailable || isLoadingDefault || isLoadingConfig;

  // Get config for a specific model
  // Extract family name: "gemma2:9b" → "gemma2", "qwen2.5:14b" → "qwen2"
  const getModelConfig = (modelName: string | undefined): ModelConfig | undefined => {
    if (!modelName || !modelsConfig) return undefined;
    // Remove tag (after colon), then remove only minor version (after dot)
    // gemma2:9b → gemma2, qwen2.5:14b → qwen2, qwen3:30b → qwen3
    const family = modelName.split(':')[0].replace(/\.\d+$/, '');
    return modelsConfig[family];
  };

  // Whisper options
  const whisperOptions = useMemo(() => {
    if (!availableModels?.whisper_models.length) {
      // Fallback to default model if no config
      return defaultModels ? [{ value: defaultModels.transcribe, label: defaultModels.transcribe }] : [];
    }
    return whisperToOptions(availableModels.whisper_models);
  }, [availableModels, defaultModels]);

  // Combined LLM options: Ollama (local) + Claude (cloud)
  const llmOptions = useMemo(() => {
    return buildLLMOptions(availableModels?.ollama_models, availableModels?.claude_models);
  }, [availableModels]);

  const handleSave = () => {
    setModels(localModels);
    closeSettings();
  };

  const handleReset = () => {
    setLocalModels({});
  };

  const handleChange = (stage: PipelineStage, value: string | undefined) => {
    setLocalModels((prev) => ({
      ...prev,
      [stage]: value,
    }));
  };

  if (!isSettingsOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/30">
      <div className="fixed inset-0" onClick={closeSettings} />
      <div className="relative w-full max-w-lg bg-white rounded-2xl shadow-xl overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100">
          <h2 className="text-lg font-semibold text-gray-900">Настройки моделей</h2>
          <button
            onClick={closeSettings}
            className="p-1.5 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-lg transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        {isLoading ? (
          <div className="flex items-center justify-center py-12">
            <Spinner size="lg" />
          </div>
        ) : (
          <>
            <div className="px-6 max-h-[60vh] overflow-y-auto">
              {/* Transcribe */}
              <div className="py-5 border-b border-gray-100">
                <ModelSelector
                  stage="transcribe"
                  value={localModels.transcribe}
                  defaultValue={defaultModels?.transcribe || ''}
                  options={whisperOptions}
                  onChange={(v) => handleChange('transcribe', v)}
                />
              </div>

              {/* Clean */}
              <div className="py-5 border-b border-gray-100">
                <ModelSelector
                  stage="clean"
                  value={localModels.clean}
                  defaultValue={defaultModels?.clean || ''}
                  options={llmOptions}
                  onChange={(v) => handleChange('clean', v)}
                  config={getModelConfig(localModels.clean || defaultModels?.clean)}
                />
              </div>

              {/* Longread */}
              <div className="py-5 border-b border-gray-100">
                <ModelSelector
                  stage="longread"
                  value={localModels.longread}
                  defaultValue={defaultModels?.longread || ''}
                  options={llmOptions}
                  onChange={(v) => handleChange('longread', v)}
                  config={getModelConfig(localModels.longread || defaultModels?.longread)}
                />
              </div>

              {/* Summarize */}
              <div className="py-5">
                <ModelSelector
                  stage="summarize"
                  value={localModels.summarize}
                  defaultValue={defaultModels?.summarize || ''}
                  options={llmOptions}
                  onChange={(v) => handleChange('summarize', v)}
                  config={getModelConfig(localModels.summarize || defaultModels?.summarize)}
                />
              </div>
            </div>

            {/* Footer */}
            <div className="flex items-center justify-between px-6 py-4 bg-gray-50 border-t border-gray-100">
              <button
                onClick={handleReset}
                className="flex items-center gap-2 px-3 py-2 text-sm text-gray-600 hover:text-gray-800 hover:bg-gray-100 rounded-lg transition-colors"
              >
                <RotateCcw className="w-4 h-4" />
                Сбросить
              </button>
              <div className="flex items-center gap-3">
                <Button variant="secondary" onClick={closeSettings}>
                  Отмена
                </Button>
                <Button onClick={handleSave}>
                  Сохранить
                </Button>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
