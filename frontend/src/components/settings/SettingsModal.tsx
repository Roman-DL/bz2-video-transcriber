import { useState, useEffect, useMemo } from 'react';
import { Modal } from '@/components/common/Modal';
import { Button } from '@/components/common/Button';
import { Spinner } from '@/components/common/Spinner';
import { ModelSelector } from '@/components/settings/ModelSelector';
import { useSettings } from '@/contexts/SettingsContext';
import { useAvailableModels, useDefaultModels, useModelsConfig } from '@/api/hooks/useModels';
import { whisperToOptions, buildLLMOptions } from '@/utils/modelUtils';
import type { ModelSettings, ModelConfig } from '@/api/types';
import { RotateCcw } from 'lucide-react';

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

  return (
    <Modal
      isOpen={isSettingsOpen}
      onClose={closeSettings}
      title="Настройки моделей"
      size="lg"
    >
      {isLoading ? (
        <div className="flex items-center justify-center py-8">
          <Spinner size="lg" />
        </div>
      ) : (
        <div className="space-y-6">
          {/* Transcribe */}
          <ModelSelector
            stage="transcribe"
            value={localModels.transcribe}
            defaultValue={defaultModels?.transcribe || ''}
            options={whisperOptions}
            onChange={(v) => handleChange('transcribe', v)}
          />

          {/* Clean */}
          <ModelSelector
            stage="clean"
            value={localModels.clean}
            defaultValue={defaultModels?.clean || ''}
            options={llmOptions}
            onChange={(v) => handleChange('clean', v)}
            config={getModelConfig(localModels.clean || defaultModels?.clean)}
          />

          {/* Longread */}
          <ModelSelector
            stage="longread"
            value={localModels.longread}
            defaultValue={defaultModels?.longread || ''}
            options={llmOptions}
            onChange={(v) => handleChange('longread', v)}
            config={getModelConfig(localModels.longread || defaultModels?.longread)}
          />

          {/* Summarize */}
          <ModelSelector
            stage="summarize"
            value={localModels.summarize}
            defaultValue={defaultModels?.summarize || ''}
            options={llmOptions}
            onChange={(v) => handleChange('summarize', v)}
            config={getModelConfig(localModels.summarize || defaultModels?.summarize)}
          />

          {/* Actions */}
          <div className="flex items-center justify-between pt-4 border-t border-gray-200">
            <Button
              variant="ghost"
              onClick={handleReset}
              className="flex items-center gap-2"
            >
              <RotateCcw className="w-4 h-4" />
              Сбросить
            </Button>
            <div className="flex gap-3">
              <Button variant="secondary" onClick={closeSettings}>
                Отмена
              </Button>
              <Button onClick={handleSave}>
                Сохранить
              </Button>
            </div>
          </div>
        </div>
      )}
    </Modal>
  );
}
