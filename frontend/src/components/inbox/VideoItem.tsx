import { Film, Play } from 'lucide-react';
import { Button } from '@/components/common/Button';

interface VideoItemProps {
  filename: string;
  onProcess: (filename: string) => void;
}

export function VideoItem({ filename, onProcess }: VideoItemProps) {
  // Parse filename to extract metadata if possible
  // Format: "2025.01.09 ПШ.SV Title (Speaker).mp4"
  const displayName = filename.replace(/\.[^/.]+$/, ''); // Remove extension

  return (
    <div className="flex items-center justify-between py-3 px-4 hover:bg-gray-50 rounded-lg transition-colors">
      <div className="flex items-center gap-3 min-w-0">
        <Film className="w-5 h-5 text-gray-400 flex-shrink-0" />
        <span className="text-sm text-gray-900 truncate" title={filename}>
          {displayName}
        </span>
      </div>
      <Button
        size="sm"
        onClick={() => onProcess(filename)}
        className="flex-shrink-0 ml-4"
      >
        <Play className="w-4 h-4 mr-1" />
        Обработать
      </Button>
    </div>
  );
}
