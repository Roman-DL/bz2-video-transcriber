import { useState, useMemo } from 'react';
import { useArchive } from '@/api/hooks/useArchive';
import { Spinner } from '@/components/common/Spinner';
import { ArchiveResultsModal } from './ArchiveResultsModal';
import {
  Archive,
  RefreshCw,
  ChevronRight,
  Folder,
  FolderOpen,
  FileText,
  Search,
} from 'lucide-react';
import type { ArchiveItem, ArchiveItemWithPath } from '@/api/types';

export function ArchiveCatalog() {
  const { data, isLoading, isError, refetch, isFetching } = useArchive();
  const [selectedItem, setSelectedItem] = useState<ArchiveItemWithPath | null>(null);
  const [searchQuery, setSearchQuery] = useState('');

  // Filter archive tree by search query
  const filteredData = useMemo(() => {
    if (!data || !searchQuery.trim()) return data;

    const query = searchQuery.toLowerCase();
    const filteredTree: Record<string, Record<string, ArchiveItem[]>> = {};

    for (const [year, events] of Object.entries(data.tree)) {
      const filteredEvents: Record<string, ArchiveItem[]> = {};

      for (const [eventFolder, items] of Object.entries(events)) {
        const filteredItems = items.filter(
          (item) =>
            item.title.toLowerCase().includes(query) ||
            item.speaker?.toLowerCase().includes(query)
        );
        if (filteredItems.length > 0) {
          filteredEvents[eventFolder] = filteredItems;
        }
      }

      if (Object.keys(filteredEvents).length > 0) {
        filteredTree[year] = filteredEvents;
      }
    }

    const total = Object.values(filteredTree)
      .flatMap((events) => Object.values(events))
      .flat().length;

    return { tree: filteredTree, total };
  }, [data, searchQuery]);

  const handleItemClick = (year: string, eventFolder: string, item: ArchiveItem) => {
    const topicFolder = item.speaker ? `${item.title} (${item.speaker})` : item.title;
    setSelectedItem({ ...item, year, eventFolder, topicFolder });
  };

  return (
    <>
      <main className="flex-1 flex flex-col bg-stone-50">
        {/* Archive Header */}
        <div className="flex items-center justify-between px-5 py-3 bg-white border-b border-gray-200">
          <div className="flex items-center gap-2">
            <Archive className="w-5 h-5 text-gray-400" />
            <h2 className="font-medium text-gray-900">Архив</h2>
            {data && (
              <span className="text-xs font-medium text-gray-400 bg-gray-100 px-2 py-0.5 rounded-full">
                {filteredData?.total ?? data.total} видео
              </span>
            )}
          </div>
          <div className="flex items-center gap-2">
            {/* Search */}
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
              <input
                type="text"
                placeholder="Поиск..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-9 pr-4 py-2 w-64 text-sm bg-gray-50 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-100 focus:border-blue-500 transition-colors"
              />
            </div>
            <button
              onClick={() => refetch()}
              disabled={isFetching}
              className="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-lg transition-colors disabled:opacity-50"
            >
              <RefreshCw className={`w-4 h-4 ${isFetching ? 'animate-spin' : ''}`} />
            </button>
          </div>
        </div>

        {/* Archive Tree */}
        <div className="flex-1 p-4 overflow-y-auto">
          {isLoading ? (
            <div className="flex items-center justify-center h-full">
              <Spinner />
            </div>
          ) : isError ? (
            <div className="flex items-center justify-center h-full text-red-500">
              <p className="text-sm">Ошибка загрузки архива</p>
            </div>
          ) : filteredData && filteredData.total > 0 ? (
            <div className="bg-white border border-gray-200 rounded-xl p-3">
              {Object.entries(filteredData.tree).map(([year, events]) => (
                <YearSection
                  key={year}
                  year={year}
                  events={events}
                  onItemClick={handleItemClick}
                  defaultExpanded={!!searchQuery}
                />
              ))}
            </div>
          ) : (
            <div className="flex items-center justify-center h-full text-gray-400">
              <p className="text-sm">
                {searchQuery ? 'Ничего не найдено' : 'Архив пуст'}
              </p>
            </div>
          )}
        </div>
      </main>

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
  defaultExpanded?: boolean;
}

function YearSection({ year, events, onItemClick, defaultExpanded = false }: YearSectionProps) {
  const [expanded, setExpanded] = useState(true);
  const totalItems = Object.values(events).flat().length;

  return (
    <div>
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center gap-2 px-2 py-1.5 rounded-lg hover:bg-gray-50 text-left"
      >
        <ChevronRight
          className={`w-4 h-4 text-gray-400 transition-transform ${expanded ? 'rotate-90' : ''}`}
        />
        {expanded ? (
          <FolderOpen className="w-4 h-4 text-amber-500" />
        ) : (
          <Folder className="w-4 h-4 text-amber-500" />
        )}
        <span className="font-medium text-gray-700">{year}</span>
        <span className="text-xs text-gray-400 ml-1">({totalItems})</span>
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
              defaultExpanded={defaultExpanded}
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
  defaultExpanded?: boolean;
}

function EventSection({
  year,
  eventFolder,
  items,
  onItemClick,
  defaultExpanded = false,
}: EventSectionProps) {
  const [expanded, setExpanded] = useState<boolean>(defaultExpanded || true);

  return (
    <div>
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center gap-2 px-2 py-1.5 rounded-lg hover:bg-gray-50 text-left"
      >
        <ChevronRight
          className={`w-4 h-4 text-gray-400 transition-transform ${expanded ? 'rotate-90' : ''}`}
        />
        {expanded ? (
          <FolderOpen className="w-4 h-4 text-amber-500" />
        ) : (
          <Folder className="w-4 h-4 text-amber-500" />
        )}
        <span className="text-sm font-medium text-gray-700">{eventFolder}</span>
        <span className="text-xs text-gray-400 ml-1">({items.length})</span>
      </button>
      {expanded && (
        <div className="ml-4">
          {items.map((item, idx) => (
            <button
              key={idx}
              onClick={() => onItemClick(year, eventFolder, item)}
              className="w-full flex items-center gap-2 px-2 py-1.5 rounded-lg text-sm hover:bg-blue-50 text-left transition-colors"
            >
              <div className="w-4" /> {/* Spacer for alignment */}
              <FileText className="w-4 h-4 text-gray-400 flex-shrink-0" />
              <span className="text-gray-600 hover:text-blue-600 truncate transition-colors">
                {item.title}
              </span>
              {item.speaker && (
                <span className="text-xs text-gray-400 ml-1 flex-shrink-0">
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
