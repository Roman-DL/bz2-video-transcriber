import type { ComponentPrompts } from '@/api/types';
import { ChevronDown } from 'lucide-react';

interface ComponentPromptSelectorProps {
  label: string;
  componentData: ComponentPrompts;
  value: string | undefined;
  onChange: (value: string | undefined) => void;
}

const COMPONENT_LABELS: Record<string, string> = {
  system: 'Системный',
  user: 'Пользовательский',
  instructions: 'Инструкции',
  template: 'Шаблон',
};

/**
 * Selector for a prompt component variant.
 * Only renders if there are multiple variants available.
 */
export function ComponentPromptSelector({
  label,
  componentData,
  value,
  onChange,
}: ComponentPromptSelectorProps) {
  // Only show selector if there are multiple variants
  if (componentData.variants.length <= 1) {
    return null;
  }

  const selectedValue = value || componentData.default;

  return (
    <div className="space-y-1">
      <label className="text-xs text-gray-500">
        {label || COMPONENT_LABELS[componentData.component] || componentData.component}
      </label>
      <div className="relative">
        <select
          value={selectedValue}
          onChange={(e) => {
            const newValue = e.target.value;
            // If selecting default, set to undefined (won't be sent in API)
            onChange(newValue === componentData.default ? undefined : newValue);
          }}
          className="block w-full rounded border border-gray-300 bg-white py-1.5 pl-2 pr-7 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 appearance-none"
        >
          {componentData.variants.map((variant) => (
            <option key={variant.name} value={variant.name}>
              {variant.name}
              {variant.name === componentData.default ? ' (по умолчанию)' : ''}
              {variant.source === 'external' ? ' *' : ''}
            </option>
          ))}
        </select>
        <ChevronDown className="absolute right-2 top-1/2 -translate-y-1/2 w-3 h-3 text-gray-400 pointer-events-none" />
      </div>
    </div>
  );
}
