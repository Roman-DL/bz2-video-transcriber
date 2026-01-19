import { Video, Settings } from 'lucide-react';
import { ServiceStatus } from '@/components/services/ServiceStatus';
import { useSettings } from '@/contexts/SettingsContext';

export function Header() {
  const { openSettings } = useSettings();

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
        <div className="flex items-center gap-3">
          <ServiceStatus />
          <button
            onClick={openSettings}
            className="p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-lg transition-colors"
            title="Настройки моделей"
          >
            <Settings className="w-5 h-5" />
          </button>
        </div>
      </div>
    </header>
  );
}
