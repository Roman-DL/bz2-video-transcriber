import { useState, useCallback } from 'react';
import { QueryClient, QueryClientProvider, useQueryClient } from '@tanstack/react-query';
import { Layout } from '@/components/layout/Layout';
import { InboxList } from '@/components/inbox/InboxList';
import { ArchiveCatalog } from '@/components/archive/ArchiveCatalog';
import { ProcessingModal } from '@/components/processing/ProcessingModal';
import { ArchiveResultsModal } from '@/components/archive/ArchiveResultsModal';
import { SettingsProvider, type ProcessingMode } from '@/contexts/SettingsContext';
import { SettingsModal } from '@/components/settings/SettingsModal';
import type { SlideFile, VideoMetadata, ArchiveItemWithPath } from '@/api/types';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

interface SelectedVideo {
  filename: string;
  mode: ProcessingMode;
  slides: SlideFile[];
}

/**
 * Convert VideoMetadata to ArchiveItemWithPath for ArchiveResultsModal.
 *
 * Archive structure (3 levels):
 * - Regular: archive/{year}/{event_type}/{MM.DD topic (speaker)}/
 * - Offsite: archive/{year}/{MM event_type}/{topic (speaker)}/
 */
function metadataToArchiveItem(metadata: VideoMetadata): ArchiveItemWithPath {
  const year = metadata.date.split('-')[0];
  const isOffsite = metadata.eventCategory === 'offsite';

  let eventGroup: string;
  let topicFolder: string;

  if (isOffsite) {
    const month = metadata.date.split('-')[1];
    eventGroup = `${month} ${metadata.eventType}`;
    topicFolder = metadata.speaker
      ? `${metadata.title} (${metadata.speaker})`
      : metadata.title;
  } else {
    eventGroup = metadata.eventType;
    const [, month, day] = metadata.date.split('-');
    const datePrefix = `${month}.${day}`;
    if (metadata.stream) {
      topicFolder = `${datePrefix} ${metadata.stream}. ${metadata.title} (${metadata.speaker})`;
    } else {
      topicFolder = `${datePrefix} ${metadata.title} (${metadata.speaker})`;
    }
  }

  return {
    title: metadata.title,
    speaker: metadata.speaker,
    eventType: eventGroup,
    year,
    eventGroup,
    topicFolder,
  };
}

function Dashboard() {
  const [selectedVideo, setSelectedVideo] = useState<SelectedVideo | null>(null);
  const [archiveItem, setArchiveItem] = useState<ArchiveItemWithPath | null>(null);
  const client = useQueryClient();

  const handleProcessVideo = (filename: string, mode: ProcessingMode, slides: SlideFile[]) => {
    setSelectedVideo({ filename, mode, slides });
  };

  const handleCloseModal = () => {
    setSelectedVideo(null);
  };

  // Handle "Open in Archive" action after processing completes
  const handleOpenArchive = useCallback((metadata: VideoMetadata) => {
    // Refetch archive to show newly saved files
    client.invalidateQueries({ queryKey: ['archive'] });

    // Open results modal with the processed item
    const item = metadataToArchiveItem(metadata);
    setArchiveItem(item);
  }, [client]);

  return (
    <>
      <InboxList onProcessVideo={handleProcessVideo} />
      <ArchiveCatalog onItemClick={setArchiveItem} />

      <ProcessingModal
        isOpen={selectedVideo !== null}
        filename={selectedVideo?.filename ?? null}
        mode={selectedVideo?.mode ?? 'step'}
        slides={selectedVideo?.slides ?? []}
        onClose={handleCloseModal}
        onOpenArchive={handleOpenArchive}
      />

      <ArchiveResultsModal
        isOpen={archiveItem !== null}
        onClose={() => setArchiveItem(null)}
        item={archiveItem}
      />
    </>
  );
}

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <SettingsProvider>
        <Layout>
          <Dashboard />
        </Layout>
        <SettingsModal />
      </SettingsProvider>
    </QueryClientProvider>
  );
}

export default App;
