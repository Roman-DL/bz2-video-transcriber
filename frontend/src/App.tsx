import { useState } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Layout } from '@/components/layout/Layout';
import { InboxList } from '@/components/inbox/InboxList';
import { JobList } from '@/components/jobs/JobList';
import { ProcessingModal } from '@/components/processing/ProcessingModal';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

function Dashboard() {
  const [selectedVideo, setSelectedVideo] = useState<string | null>(null);

  return (
    <>
      <div className="max-w-6xl mx-auto">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <InboxList onProcessVideo={setSelectedVideo} />
          <JobList />
        </div>
      </div>

      <ProcessingModal
        isOpen={selectedVideo !== null}
        filename={selectedVideo}
        onClose={() => setSelectedVideo(null)}
      />
    </>
  );
}

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <Layout>
        <Dashboard />
      </Layout>
    </QueryClientProvider>
  );
}

export default App;
