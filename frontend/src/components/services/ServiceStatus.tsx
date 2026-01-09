import { useServices } from '@/api/hooks/useServices';

export function ServiceStatus() {
  const { data, isLoading, isError } = useServices();

  if (isLoading) {
    return (
      <div className="flex items-center gap-4 text-sm text-gray-500">
        <span>Проверка сервисов...</span>
      </div>
    );
  }

  if (isError || !data) {
    return (
      <div className="flex items-center gap-4 text-sm">
        <StatusIndicator name="Whisper" status={false} />
        <StatusIndicator name="Ollama" status={false} />
      </div>
    );
  }

  return (
    <div className="flex items-center gap-4 text-sm">
      <StatusIndicator name="Whisper" status={data.whisper} />
      <StatusIndicator name="Ollama" status={data.ollama} />
    </div>
  );
}

function StatusIndicator({ name, status }: { name: string; status: boolean }) {
  return (
    <div className="flex items-center gap-1.5">
      <div
        className={`w-2 h-2 rounded-full ${
          status ? 'bg-green-500' : 'bg-red-500'
        }`}
      />
      <span className={status ? 'text-gray-700' : 'text-red-600'}>{name}</span>
    </div>
  );
}
