import { Video, Settings } from 'lucide-react';
import { ServiceStatus } from '@/components/services/ServiceStatus';
import { useSettings } from '@/contexts/SettingsContext';

export function Header() {
  const { openSettings } = useSettings();

  return (
    <header className="flex items-center justify-between px-6 py-4 bg-white border-b border-gray-200">
      <div className="flex items-center gap-3">
        <div className="p-2 bg-gradient-to-br from-blue-500 to-blue-600 rounded-lg">
          <Video className="w-5 h-5 text-white" />
        </div>
        <div>
          <h1 className="text-lg font-semibold text-gray-900">БЗ Транскрибатор</h1>
          <span className="text-xs text-gray-400">
            v{__APP_VERSION__} • {__BUILD_TIME__}
          </span>
        </div>
      </div>

      <div className="flex items-center gap-6">
        <ServiceStatus />
        <button
          onClick={openSettings}
          className="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-lg transition-colors"
          title="Настройки моделей"
        >
          <Settings className="w-5 h-5" />
        </button>
      </div>
    </header>
  );
}
