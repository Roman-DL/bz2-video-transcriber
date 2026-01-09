import { Video } from 'lucide-react';
import { ServiceStatus } from '@/components/services/ServiceStatus';

export function Header() {
  return (
    <header className="bg-white border-b border-gray-200 px-6 py-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Video className="w-6 h-6 text-blue-600" />
          <h1 className="text-xl font-semibold text-gray-900">
            БЗ2 Транскрибатор
          </h1>
          <span className="text-xs text-gray-400">
            v{__APP_VERSION__} • {__BUILD_TIME__}
          </span>
        </div>
        <ServiceStatus />
      </div>
    </header>
  );
}
