import { useState } from 'react';
import { Film, Music, Zap, ListOrdered, ChevronDown, Check } from 'lucide-react';
import { isAudioFile } from '@/utils/fileUtils';
import type { ProcessingMode } from '@/contexts/SettingsContext';

interface VideoItemProps {
  filename: string;
  defaultMode: ProcessingMode;
  onProcess: (filename: string, mode: ProcessingMode) => void;
  onModeChange: (mode: ProcessingMode) => void;
}

/**
 * Parse filename to extract display name and speaker.
 * Formats:
 * - "2025.01.09 ПШ.SV Title (Speaker).mp4" -> { name: "2025.01.09 ПШ.SV Title", speaker: "Speaker" }
 * - "2026.01 Форум Табтим. # Антоновы (Дмитрий и Юлия).mp3" -> { name: "2026.01 Форум Табтим. # Антоновы", speaker: "Дмитрий и Юлия" }
 */
function parseFilename(filename: string): { name: string; speaker: string | null } {
  const withoutExt = filename.replace(/\.[^/.]+$/, '');
  const match = withoutExt.match(/^(.+?)\s*\(([^)]+)\)$/);
  if (match) {
    return { name: match[1].trim(), speaker: match[2].trim() };
  }
  return { name: withoutExt, speaker: null };
}

const MODES = [
  {
    id: 'step' as ProcessingMode,
    name: 'Пошагово',
    icon: ListOrdered,
    description: 'Контроль каждого этапа',
  },
  {
    id: 'auto' as ProcessingMode,
    name: 'Авто',
    icon: Zap,
    description: 'Все этапы без остановок',
  },
];

interface ProcessButtonProps {
  filename: string;
  defaultMode: ProcessingMode;
  onProcess: (filename: string, mode: ProcessingMode) => void;
  onModeChange: (mode: ProcessingMode) => void;
}

function ProcessButton({ filename, defaultMode, onProcess, onModeChange }: ProcessButtonProps) {
  const [isOpen, setIsOpen] = useState(false);

  const currentMode = MODES.find((m) => m.id === defaultMode) || MODES[0];
  const CurrentIcon = currentMode.icon;

  return (
    <div className="relative">
      <div className="flex">
        {/* Main button */}
        <button
          onClick={() => onProcess(filename, defaultMode)}
          className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-white bg-blue-500 rounded-l-lg hover:bg-blue-600 transition-colors"
        >
          <CurrentIcon className="w-3.5 h-3.5" />
          {currentMode.name}
        </button>

        {/* Dropdown trigger */}
        <button
          onClick={() => setIsOpen(!isOpen)}
          className="flex items-center px-1.5 py-1.5 text-white bg-blue-500 border-l border-blue-400 rounded-r-lg hover:bg-blue-600 transition-colors"
        >
          <ChevronDown className={`w-3.5 h-3.5 transition-transform ${isOpen ? 'rotate-180' : ''}`} />
        </button>
      </div>

      {/* Dropdown menu */}
      {isOpen && (
        <>
          <div className="fixed inset-0 z-10" onClick={() => setIsOpen(false)} />
          <div className="absolute right-0 z-20 mt-1 w-48 bg-white border border-gray-200 rounded-xl shadow-lg overflow-hidden">
            {MODES.map((mode) => {
              const Icon = mode.icon;
              const isSelected = mode.id === defaultMode;
              return (
                <button
                  key={mode.id}
                  onClick={() => {
                    onModeChange(mode.id);
                    onProcess(filename, mode.id);
                    setIsOpen(false);
                  }}
                  className={`w-full flex items-start gap-3 px-3 py-2.5 text-left hover:bg-gray-50 transition-colors ${
                    isSelected ? 'bg-blue-50' : ''
                  }`}
                >
                  <div
                    className={`p-1.5 rounded-lg ${
                      isSelected ? 'bg-blue-100 text-blue-600' : 'bg-gray-100 text-gray-500'
                    }`}
                  >
                    <Icon className="w-4 h-4" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className={`text-sm font-medium ${isSelected ? 'text-blue-600' : 'text-gray-900'}`}>
                        {mode.name}
                      </span>
                      {isSelected && <Check className="w-3.5 h-3.5 text-blue-500" />}
                    </div>
                    <p className="text-xs text-gray-500 mt-0.5">{mode.description}</p>
                  </div>
                </button>
              );
            })}
          </div>
        </>
      )}
    </div>
  );
}

export function VideoItem({ filename, defaultMode, onProcess, onModeChange }: VideoItemProps) {
  const { name, speaker } = parseFilename(filename);
  const isAudio = isAudioFile(filename);
  const FileIcon = isAudio ? Music : Film;

  return (
    <div className="bg-white border border-gray-200 rounded-xl p-4 hover:border-blue-300 hover:shadow-md transition-all group">
      <div className="flex items-start gap-3 mb-3">
        <div
          className={`p-2 rounded-lg flex-shrink-0 ${
            isAudio ? 'bg-violet-50 text-violet-500' : 'bg-sky-50 text-sky-500'
          }`}
        >
          <FileIcon className="w-5 h-5" />
        </div>
        <div className="flex-1 min-w-0">
          <h3 className="text-sm font-medium text-gray-900 leading-snug mb-1 line-clamp-2" title={filename}>
            {name}
          </h3>
          {speaker && <p className="text-xs text-gray-400">{speaker}</p>}
        </div>
      </div>

      <div className="flex items-center justify-end">
        <ProcessButton
          filename={filename}
          defaultMode={defaultMode}
          onProcess={onProcess}
          onModeChange={onModeChange}
        />
      </div>
    </div>
  );
}
