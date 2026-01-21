/**
 * Reusable model selector component with compact and full modes.
 */
import { ChevronDown } from 'lucide-react';
import type { ModelOption } from '@/utils/modelUtils';
import type { ModelConfig, StageConfig } from '@/api/types';

type PipelineStage = 'transcribe' | 'clean' | 'longread' | 'summarize';

const STAGE_LABELS: Record<PipelineStage, string> = {
  transcribe: 'Транскрипция',
  clean: 'Очистка',
  longread: 'Лонгрид',
  summarize: 'Конспект',
};

const STAGE_CONFIG_KEYS: Record<PipelineStage, keyof ModelConfig | null> = {
  transcribe: null, // Whisper doesn't have config in models.yaml
  clean: 'cleaner',
  longread: null, // Longread doesn't have stage-specific config
  summarize: null, // Summarizer doesn't have stage-specific config
};

function formatTokens(tokens: number): string {
  if (tokens >= 1000) {
    return `${Math.round(tokens / 1024)}K токенов`;
  }
  return `${tokens} токенов`;
}

interface ModelSelectorProps {
  /** Label for the selector. In full mode, uses STAGE_LABELS if stage provided */
  label?: string;
  /** Stage name (for full mode with STAGE_LABELS) */
  stage?: PipelineStage;
  /** Currently selected value (undefined = default) */
  value: string | undefined;
  /** Default value to use when value is undefined */
  defaultValue: string;
  /** Available model options */
  options: ModelOption[];
  /** Callback when selection changes */
  onChange: (value: string | undefined) => void;
  /** Disable the selector */
  disabled?: boolean;
  /** Compact mode for step-by-step UI (no config info) */
  compact?: boolean;
  /** Model config for full mode (shows context tokens, stage params) */
  config?: ModelConfig;
}

export function ModelSelector({
  label,
  stage,
  value,
  defaultValue,
  options,
  onChange,
  disabled,
  compact = false,
  config,
}: ModelSelectorProps) {
  const isDefault = !value;
  const selectedValue = value || defaultValue;

  // Get stage-specific config (only in full mode)
  const stageConfigKey = stage ? STAGE_CONFIG_KEYS[stage] : null;
  const rawStageConfig = stageConfigKey && config ? config[stageConfigKey] : null;
  // Ensure we only use StageConfig objects, not numbers (like context_tokens)
  const stageConfig: StageConfig | null = rawStageConfig && typeof rawStageConfig === 'object' ? rawStageConfig : null;

  // Find selected option for description and provider info
  const selectedOption = options.find((o) => o.value === selectedValue);
  const isCloudModel = selectedOption?.provider === 'cloud';

  // Determine display label
  const displayLabel = label || (stage ? STAGE_LABELS[stage] : 'Модель');

  if (compact) {
    return (
      <div className="space-y-1">
        <div className="flex items-center gap-2">
          <label className="text-xs text-gray-500">{displayLabel}</label>
          {isCloudModel && (
            <span className="inline-flex items-center px-1.5 py-0.5 rounded text-xs bg-blue-100 text-blue-700">
              cloud
            </span>
          )}
        </div>
        <div className="relative">
          <select
            value={selectedValue}
            onChange={(e) => {
              const newValue = e.target.value;
              onChange(newValue === defaultValue ? undefined : newValue);
            }}
            disabled={disabled}
            className="block w-full rounded-md border border-gray-300 bg-white py-1.5 pl-2 pr-7 text-xs focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 appearance-none disabled:bg-gray-100 disabled:cursor-not-allowed"
          >
            {options.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
                {opt.value === defaultValue ? ' (default)' : ''}
              </option>
            ))}
          </select>
          <ChevronDown className="absolute right-2 top-1/2 -translate-y-1/2 w-3 h-3 text-gray-400 pointer-events-none" />
        </div>
      </div>
    );
  }

  // Full mode (for SettingsModal)
  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2">
        <label className="block text-sm font-medium text-gray-700">
          {displayLabel}
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
            onChange(newValue === defaultValue ? undefined : newValue);
          }}
          disabled={disabled}
          className="block w-full rounded-lg border border-gray-300 bg-white py-2 pl-3 pr-10 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 appearance-none disabled:bg-gray-100 disabled:cursor-not-allowed"
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
