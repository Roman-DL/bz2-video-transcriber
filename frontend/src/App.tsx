import { useState, useCallback } from 'react';
import { QueryClient, QueryClientProvider, useQueryClient } from '@tanstack/react-query';
import { Layout } from '@/components/layout/Layout';
import { InboxList } from '@/components/inbox/InboxList';
import { ArchiveCatalog } from '@/components/archive/ArchiveCatalog';
import { ProcessingModal } from '@/components/processing/ProcessingModal';
import { SettingsProvider, type ProcessingMode } from '@/contexts/SettingsContext';
import { SettingsModal } from '@/components/settings/SettingsModal';
import type { SlideFile } from '@/api/types';

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

function Dashboard() {
  const [selectedVideo, setSelectedVideo] = useState<SelectedVideo | null>(null);
  const client = useQueryClient();

  const handleProcessVideo = (filename: string, mode: ProcessingMode, slides: SlideFile[]) => {
    setSelectedVideo({ filename, mode, slides });
  };

  const handleCloseModal = () => {
    setSelectedVideo(null);
  };

  // Handle "Open in Archive" action after processing completes
  const handleOpenArchive = useCallback((archivePath: string) => {
    // Refetch archive to show newly saved files
    client.invalidateQueries({ queryKey: ['archive'] });

    // Future enhancement: could scroll to specific item using archivePath
    // For now, just refresh the archive list
    console.log('Opening archive path:', archivePath);
  }, [client]);

  return (
    <>
      <InboxList onProcessVideo={handleProcessVideo} />
      <ArchiveCatalog />

      <ProcessingModal
        isOpen={selectedVideo !== null}
        filename={selectedVideo?.filename ?? null}
        mode={selectedVideo?.mode ?? 'step'}
        slides={selectedVideo?.slides ?? []}
        onClose={handleCloseModal}
        onOpenArchive={handleOpenArchive}
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
