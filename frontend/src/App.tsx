import { useState } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
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

  const handleProcessVideo = (filename: string, mode: ProcessingMode, slides: SlideFile[]) => {
    setSelectedVideo({ filename, mode, slides });
  };

  return (
    <>
      <InboxList onProcessVideo={handleProcessVideo} />
      <ArchiveCatalog />

      <ProcessingModal
        isOpen={selectedVideo !== null}
        filename={selectedVideo?.filename ?? null}
        mode={selectedVideo?.mode ?? 'step'}
        slides={selectedVideo?.slides ?? []}
        onClose={() => setSelectedVideo(null)}
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
