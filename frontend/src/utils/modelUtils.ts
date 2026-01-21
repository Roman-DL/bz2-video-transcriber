/**
 * Shared utilities for model selection across settings and step-by-step mode.
 */
import type { WhisperModelConfig, ClaudeModelConfig, ProviderType } from '@/api/types';

export interface ModelOption {
  value: string;
  label: string;
  description?: string;
  provider?: ProviderType;
}

/** Convert whisper models from config to options format */
export function whisperToOptions(models: WhisperModelConfig[]): ModelOption[] {
  return models.map((m) => ({
    value: m.id,
    label: m.name,
    description: m.description,
  }));
}

/** Convert ollama model names to options format */
export function ollamaToOptions(models: string[]): ModelOption[] {
  return models.map((m) => ({ value: m, label: m, provider: 'local' as ProviderType }));
}

/** Convert claude models from config to options format */
export function claudeToOptions(models: ClaudeModelConfig[]): ModelOption[] {
  return models.map((m) => ({
    value: m.id,
    label: `☁️ ${m.name}`,
    description: m.description,
    provider: 'cloud' as ProviderType,
  }));
}

/** Build combined LLM options from available models */
export function buildLLMOptions(
  ollamaModels?: string[],
  claudeModels?: ClaudeModelConfig[]
): ModelOption[] {
  const options: ModelOption[] = [];
  if (ollamaModels?.length) {
    options.push(...ollamaToOptions(ollamaModels));
  }
  if (claudeModels?.length) {
    options.push(...claudeToOptions(claudeModels));
  }
  return options;
}
