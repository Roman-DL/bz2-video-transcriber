import { Film, Music, Play } from 'lucide-react';
import { isAudioFile } from '@/utils/fileUtils';

interface VideoItemProps {
  filename: string;
  onProcess: (filename: string) => void;
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

export function VideoItem({ filename, onProcess }: VideoItemProps) {
  const { name, speaker } = parseFilename(filename);
  const isAudio = isAudioFile(filename);
  const FileIcon = isAudio ? Music : Film;

  return (
    <div className="bg-white border border-gray-200 rounded-xl p-4 hover:border-blue-300 hover:shadow-md transition-all group">
      <div className="flex items-start gap-3 mb-3">
        <div className={`p-2 rounded-lg flex-shrink-0 ${
          isAudio ? 'bg-violet-50 text-violet-500' : 'bg-sky-50 text-sky-500'
        }`}>
          <FileIcon className="w-5 h-5" />
        </div>
        <div className="flex-1 min-w-0">
          <h3 className="text-sm font-medium text-gray-900 leading-snug mb-1 line-clamp-2" title={filename}>
            {name}
          </h3>
          {speaker && (
            <p className="text-xs text-gray-400">
              {speaker}
            </p>
          )}
        </div>
      </div>

      <div className="flex items-center justify-end">
        <button
          onClick={() => onProcess(filename)}
          className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-white bg-blue-500 rounded-lg hover:bg-blue-600 transition-colors opacity-80 group-hover:opacity-100"
        >
          <Play className="w-3 h-3" />
          Обработать
        </button>
      </div>
    </div>
  );
}
