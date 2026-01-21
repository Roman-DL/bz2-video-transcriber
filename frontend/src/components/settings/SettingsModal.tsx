import { useState, useEffect, useMemo } from 'react';
import { Modal } from '@/components/common/Modal';
import { Button } from '@/components/common/Button';
import { Spinner } from '@/components/common/Spinner';
import { useSettings } from '@/contexts/SettingsContext';
import { useAvailableModels, useDefaultModels, useModelsConfig } from '@/api/hooks/useModels';
import type { ModelSettings, ModelConfig, WhisperModelConfig, ClaudeModelConfig, ProviderType } from '@/api/types';
import { ChevronDown, RotateCcw } from 'lucide-react';

type PipelineStage = 'transcribe' | 'clean' | 'summarize';

const STAGE_LABELS: Record<PipelineStage, string> = {
  transcribe: 'Транскрипция',
  clean: 'Очистка',
  summarize: 'Суммаризация',
};

const STAGE_CONFIG_KEYS: Record<PipelineStage, keyof ModelConfig | null> = {
  transcribe: null, // Whisper doesn't have config in models.yaml
  clean: 'cleaner',
  summarize: null, // Summarizer doesn't have stage-specific config
};

interface ModelOption {
  value: string;
  label: string;
  description?: string;
  provider?: ProviderType;
}

interface ModelSelectorProps {
  stage: PipelineStage;
  value: string | undefined;
  defaultValue: string;
  options: ModelOption[];
  onChange: (value: string | undefined) => void;
  config?: ModelConfig;
}

function ModelSelector({ stage, value, defaultValue, options, onChange, config }: ModelSelectorProps) {
  const isDefault = !value;
  const selectedValue = value || defaultValue;

  const stageConfigKey = STAGE_CONFIG_KEYS[stage];
  const stageConfig = stageConfigKey && config ? config[stageConfigKey] : null;

  // Find selected option for description and provider info
  const selectedOption = options.find((o) => o.value === selectedValue);
  const isCloudModel = selectedOption?.provider === 'cloud';

  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2">
        <label className="block text-sm font-medium text-gray-700">
          {STAGE_LABELS[stage]}
        </label>
        {isCloudModel && (
          <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-blue-100 text-blue-800">
            ☁️ Cloud
          </span>
        )}
      </div>
      <div className="relative">
        <select
          value={selectedValue}
          onChange={(e) => {
            const newValue = e.target.value;
            // If selecting default value, set to undefined
            onChange(newValue === defaultValue ? undefined : newValue);
          }}
          className="block w-full rounded-lg border border-gray-300 bg-white py-2 pl-3 pr-10 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 appearance-none"
        >
          {options.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
              {opt.value === defaultValue ? ' (по умолчанию)' : ''}
            </option>
          ))}
        </select>
        <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400 pointer-events-none" />
      </div>

      {/* Description for whisper/claude models */}
      {selectedOption?.description && (
        <p className="text-xs text-gray-500">{selectedOption.description}</p>
      )}

      {/* Model config info */}
      {config && (
        <div className="mt-2 p-3 bg-gray-50 rounded-lg text-xs text-gray-600">
          {config.context_tokens && (
            <div className="flex items-center gap-1 mb-1">
              <span className="font-medium">Контекст:</span>
              <span>{formatTokens(config.context_tokens)}</span>
            </div>
          )}
          {stageConfig && (
            <div className="flex flex-wrap gap-x-3 gap-y-1">
              {Object.entries(stageConfig).map(([key, val]) => (
                <span key={key}>
                  {key}: <span className="font-medium">{val}</span>
                </span>
              ))}
            </div>
          )}
          {!config.context_tokens && !stageConfig && (
            <span className="text-gray-400">Параметры по умолчанию</span>
          )}
        </div>
      )}

      {isDefault && (
        <p className="text-xs text-gray-400">Использует настройки сервера</p>
      )}
    </div>
  );
}

/** Convert whisper models from config to options format */
function whisperToOptions(models: WhisperModelConfig[]): ModelOption[] {
  return models.map((m) => ({
    value: m.id,
    label: m.name,
    description: m.description,
  }));
}

/** Convert ollama model names to options format */
function ollamaToOptions(models: string[]): ModelOption[] {
  return models.map((m) => ({ value: m, label: m, provider: 'local' as ProviderType }));
}

/** Convert claude models from config to options format */
function claudeToOptions(models: ClaudeModelConfig[]): ModelOption[] {
  return models.map((m) => ({
    value: m.id,
    label: `☁️ ${m.name}`,
    description: m.description,
    provider: 'cloud' as ProviderType,
  }));
}

function formatTokens(tokens: number): string {
  if (tokens >= 1000) {
    return `${Math.round(tokens / 1024)}K токенов`;
  }
  return `${tokens} токенов`;
}

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

  // Determine which models to show for each stage
  const whisperOptions = useMemo((): ModelOption[] => {
    if (!availableModels?.whisper_models.length) {
      // Fallback to default model if no config
      return defaultModels ? [{ value: defaultModels.transcribe, label: defaultModels.transcribe }] : [];
    }
    return whisperToOptions(availableModels.whisper_models);
  }, [availableModels, defaultModels]);

  // Combined LLM options: Ollama (local) + Claude (cloud)
  const llmOptions = useMemo((): ModelOption[] => {
    const options: ModelOption[] = [];

    // Ollama models (local)
    if (availableModels?.ollama_models.length) {
      options.push(...ollamaToOptions(availableModels.ollama_models));
    } else if (defaultModels) {
      // Fallback to default models
      const defaults = new Set([defaultModels.clean, defaultModels.summarize]);
      options.push(...ollamaToOptions(Array.from(defaults)));
    }

    // Claude models (cloud) - only if available
    if (availableModels?.claude_models?.length) {
      options.push(...claudeToOptions(availableModels.claude_models));
    }

    return options;
  }, [availableModels, defaultModels]);

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
