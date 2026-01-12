import { useState } from 'react';
import { useArchive } from '@/api/hooks/useArchive';
import { Card, CardContent, CardHeader } from '@/components/common/Card';
import { Spinner } from '@/components/common/Spinner';
import { Button } from '@/components/common/Button';
import { ArchiveResultsModal } from './ArchiveResultsModal';
import {
  Archive,
  RefreshCw,
  ChevronRight,
  ChevronDown,
  Folder,
  FileText,
} from 'lucide-react';
import type { ArchiveItem, ArchiveItemWithPath } from '@/api/types';

export function ArchiveCatalog() {
  const { data, isLoading, isError, refetch, isFetching } = useArchive();
  const [selectedItem, setSelectedItem] = useState<ArchiveItemWithPath | null>(
    null
  );

  const handleItemClick = (
    year: string,
    eventFolder: string,
    item: ArchiveItem
  ) => {
    // Reconstruct topic folder name: "title (speaker)" or just "title"
    const topicFolder = item.speaker
      ? `${item.title} (${item.speaker})`
      : item.title;

    setSelectedItem({
      ...item,
      year,
      eventFolder,
      topicFolder,
    });
  };

  return (
    <>
      <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Archive className="w-5 h-5 text-gray-500" />
            <h2 className="text-lg font-medium text-gray-900">Архив</h2>
            {data && (
              <span className="text-sm text-gray-500">({data.total} видео)</span>
            )}
          </div>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => refetch()}
            disabled={isFetching}
          >
            <RefreshCw
              className={`w-4 h-4 ${isFetching ? 'animate-spin' : ''}`}
            />
          </Button>
        </div>
      </CardHeader>
      <CardContent className="p-0">
        {isLoading ? (
          <div className="flex items-center justify-center py-8">
            <Spinner />
          </div>
        ) : isError ? (
          <div className="text-center py-8 text-red-600">
            Ошибка загрузки архива
          </div>
        ) : data && data.total > 0 ? (
          <div className="py-2">
            {Object.entries(data.tree).map(([year, events]) => (
              <YearSection
                key={year}
                year={year}
                events={events}
                onItemClick={handleItemClick}
              />
            ))}
          </div>
        ) : (
          <div className="text-center py-8 text-gray-500">Архив пуст</div>
        )}
      </CardContent>
    </Card>

      <ArchiveResultsModal
        isOpen={selectedItem !== null}
        onClose={() => setSelectedItem(null)}
        item={selectedItem}
      />
    </>
  );
}

interface YearSectionProps {
  year: string;
  events: Record<string, ArchiveItem[]>;
  onItemClick: (year: string, eventFolder: string, item: ArchiveItem) => void;
}

function YearSection({ year, events, onItemClick }: YearSectionProps) {
  const [expanded, setExpanded] = useState(true);
  const totalItems = Object.values(events).flat().length;

  return (
    <div>
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center gap-2 px-4 py-2 hover:bg-gray-50 text-left"
      >
        {expanded ? (
          <ChevronDown className="w-4 h-4 text-gray-400" />
        ) : (
          <ChevronRight className="w-4 h-4 text-gray-400" />
        )}
        <Folder className="w-4 h-4 text-amber-500" />
        <span className="font-medium text-gray-900">{year}</span>
        <span className="text-sm text-gray-500">({totalItems})</span>
      </button>
      {expanded && (
        <div className="ml-4">
          {Object.entries(events).map(([eventFolder, items]) => (
            <EventSection
              key={eventFolder}
              year={year}
              eventFolder={eventFolder}
              items={items}
              onItemClick={onItemClick}
            />
          ))}
        </div>
      )}
    </div>
  );
}

interface EventSectionProps {
  year: string;
  eventFolder: string;
  items: ArchiveItem[];
  onItemClick: (year: string, eventFolder: string, item: ArchiveItem) => void;
}

function EventSection({
  year,
  eventFolder,
  items,
  onItemClick,
}: EventSectionProps) {
  const [expanded, setExpanded] = useState(true);

  return (
    <div>
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center gap-2 px-4 py-1.5 hover:bg-gray-50 text-left"
      >
        {expanded ? (
          <ChevronDown className="w-4 h-4 text-gray-400" />
        ) : (
          <ChevronRight className="w-4 h-4 text-gray-400" />
        )}
        <Folder className="w-4 h-4 text-blue-500" />
        <span className="text-gray-700">{eventFolder}</span>
        <span className="text-sm text-gray-500">({items.length})</span>
      </button>
      {expanded && (
        <div className="ml-4">
          {items.map((item, idx) => (
            <button
              key={idx}
              onClick={() => onItemClick(year, eventFolder, item)}
              className="w-full flex items-center gap-2 px-4 py-1.5 text-sm hover:bg-gray-50 text-left"
            >
              <FileText className="w-4 h-4 text-gray-400 flex-shrink-0" />
              <span className="text-gray-700 truncate">{item.title}</span>
              {item.speaker && (
                <span className="text-gray-500 truncate flex-shrink-0">
                  ({item.speaker})
                </span>
              )}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
