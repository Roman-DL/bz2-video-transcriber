import { useState } from 'react';

// Inline SVG Icons
const Icons = {
  X: ({ className }) => (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <line x1="18" y1="6" x2="6" y2="18"/>
      <line x1="6" y1="6" x2="18" y2="18"/>
    </svg>
  ),
  Cloud: ({ className }) => (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M17.5 19H9a7 7 0 1 1 6.71-9h1.79a4.5 4.5 0 1 1 0 9Z"/>
    </svg>
  ),
  Server: ({ className }) => (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <rect width="20" height="8" x="2" y="2" rx="2" ry="2"/>
      <rect width="20" height="8" x="2" y="14" rx="2" ry="2"/>
      <line x1="6" y1="6" x2="6.01" y2="6"/>
      <line x1="6" y1="18" x2="6.01" y2="18"/>
    </svg>
  ),
  ChevronDown: ({ className }) => (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="6 9 12 15 18 9"/>
    </svg>
  ),
  Check: ({ className }) => (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="20 6 9 17 4 12"/>
    </svg>
  ),
  RefreshCw: ({ className }) => (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="23 4 23 10 17 10"/>
      <polyline points="1 20 1 14 7 14"/>
      <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/>
    </svg>
  ),
};

// Model data
const localModels = [
  { id: 'gemma2:9b', name: 'gemma2:9b', type: 'local' },
  { id: 'mistral:7b-instruct', name: 'mistral:7b-instruct', type: 'local' },
  { id: 'phi3:14b', name: 'phi3:14b', type: 'local' },
  { id: 'qwen2.5:14b', name: 'qwen2.5:14b', type: 'local' },
  { id: 'qwen2.5:7b', name: 'qwen2.5:7b', type: 'local' },
  { id: 'qwen3:14b', name: 'qwen3:14b', type: 'local' },
];

const cloudModels = [
  { 
    id: 'claude-sonnet-4.5', 
    name: 'Claude Sonnet 4.5', 
    type: 'cloud',
    description: 'Быстрая и умная ($3/$15 за 1M токенов)',
    context: '195K токенов',
    isDefault: true,
  },
  { 
    id: 'claude-haiku-4.5', 
    name: 'Claude Haiku 4.5', 
    type: 'cloud',
    description: 'Самая быстрая ($0.25/$1.25 за 1M токенов)',
    context: '195K токенов',
  },
  { 
    id: 'claude-opus-4.5', 
    name: 'Claude Opus 4.5', 
    type: 'cloud',
    description: 'Самая умная ($15/$75 за 1M токенов)',
    context: '195K токенов',
  },
];

const whisperModels = [
  { id: 'large-v3-turbo', name: 'large-v3-turbo', description: 'Быстрее, хорошее качество', isDefault: true },
  { id: 'large-v3', name: 'large-v3', description: 'Лучшее качество, медленнее' },
  { id: 'medium', name: 'medium', description: 'Средний баланс' },
  { id: 'small', name: 'small', description: 'Быстрый, базовое качество' },
];

const allLLMModels = [...localModels, ...cloudModels];

// Custom Select Component
function ModelSelect({ value, onChange, options, showCloudBadge = true }) {
  const [isOpen, setIsOpen] = useState(false);
  const selectedModel = options.find(m => m.id === value) || options[0];
  
  return (
    <div className="relative">
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className="w-full flex items-center justify-between px-4 py-3 bg-white border border-gray-200 rounded-xl text-left hover:border-gray-300 focus:outline-none focus:ring-2 focus:ring-blue-100 focus:border-blue-500 transition-colors"
      >
        <div className="flex items-center gap-2">
          {selectedModel.type === 'cloud' && showCloudBadge && (
            <Icons.Cloud className="w-4 h-4 text-blue-500" />
          )}
          {selectedModel.type === 'local' && showCloudBadge && (
            <Icons.Server className="w-4 h-4 text-gray-400" />
          )}
          <span className="text-sm text-gray-900">
            {selectedModel.name}
            {selectedModel.isDefault && (
              <span className="text-gray-400 ml-1">(по умолчанию)</span>
            )}
          </span>
        </div>
        <Icons.ChevronDown className={`w-4 h-4 text-gray-400 transition-transform ${isOpen ? 'rotate-180' : ''}`} />
      </button>
      
      {isOpen && (
        <>
          <div 
            className="fixed inset-0 z-10" 
            onClick={() => setIsOpen(false)}
          />
          <div className="absolute z-20 w-full mt-1 bg-white border border-gray-200 rounded-xl shadow-lg overflow-hidden">
            <div className="max-h-64 overflow-y-auto py-1">
              {/* Local models section */}
              {options.some(m => m.type === 'local') && (
                <>
                  {options.filter(m => m.type === 'local').map((model) => (
                    <button
                      key={model.id}
                      type="button"
                      onClick={() => {
                        onChange(model.id);
                        setIsOpen(false);
                      }}
                      className={`w-full flex items-center gap-2 px-4 py-2.5 text-left hover:bg-gray-50 transition-colors ${
                        value === model.id ? 'bg-blue-50' : ''
                      }`}
                    >
                      {value === model.id ? (
                        <Icons.Check className="w-4 h-4 text-blue-500" />
                      ) : (
                        <div className="w-4" />
                      )}
                      <Icons.Server className="w-4 h-4 text-gray-400" />
                      <span className="text-sm text-gray-700">{model.name}</span>
                    </button>
                  ))}
                </>
              )}
              
              {/* Cloud models section */}
              {options.some(m => m.type === 'cloud') && (
                <>
                  {options.filter(m => m.type === 'cloud').map((model) => (
                    <button
                      key={model.id}
                      type="button"
                      onClick={() => {
                        onChange(model.id);
                        setIsOpen(false);
                      }}
                      className={`w-full flex items-center gap-2 px-4 py-2.5 text-left hover:bg-gray-50 transition-colors ${
                        value === model.id ? 'bg-blue-50' : ''
                      }`}
                    >
                      {value === model.id ? (
                        <Icons.Check className="w-4 h-4 text-blue-500" />
                      ) : (
                        <div className="w-4" />
                      )}
                      <Icons.Cloud className="w-4 h-4 text-blue-500" />
                      <span className="text-sm text-gray-700">
                        {model.name}
                        {model.isDefault && (
                          <span className="text-gray-400 ml-1">(по умолчанию)</span>
                        )}
                      </span>
                    </button>
                  ))}
                </>
              )}
              
              {/* Whisper models (no type) */}
              {options.some(m => !m.type) && (
                <>
                  {options.filter(m => !m.type).map((model) => (
                    <button
                      key={model.id}
                      type="button"
                      onClick={() => {
                        onChange(model.id);
                        setIsOpen(false);
                      }}
                      className={`w-full flex items-center gap-2 px-4 py-2.5 text-left hover:bg-gray-50 transition-colors ${
                        value === model.id ? 'bg-blue-50' : ''
                      }`}
                    >
                      {value === model.id ? (
                        <Icons.Check className="w-4 h-4 text-blue-500" />
                      ) : (
                        <div className="w-4" />
                      )}
                      <span className="text-sm text-gray-700">
                        {model.name}
                        {model.isDefault && (
                          <span className="text-gray-400 ml-1">(по умолчанию)</span>
                        )}
                      </span>
                    </button>
                  ))}
                </>
              )}
            </div>
          </div>
        </>
      )}
    </div>
  );
}

// Settings Section Component
function SettingsSection({ title, badge, children }) {
  return (
    <div className="py-5 border-b border-gray-100 last:border-b-0">
      <div className="flex items-center gap-2 mb-3">
        <h3 className="text-sm font-medium text-gray-900">{title}</h3>
        {badge && (
          <span className={`inline-flex items-center gap-1 px-2 py-0.5 text-xs font-medium rounded-full ${
            badge === 'Cloud' 
              ? 'bg-blue-50 text-blue-600' 
              : 'bg-gray-100 text-gray-600'
          }`}>
            {badge === 'Cloud' && <Icons.Cloud className="w-3 h-3" />}
            {badge}
          </span>
        )}
      </div>
      {children}
    </div>
  );
}

// Model Info Component
function ModelInfo({ description, context, note }) {
  return (
    <div className="mt-2 space-y-1">
      {description && (
        <p className="text-xs text-gray-500">{description}</p>
      )}
      {context && (
        <div className="inline-block px-2 py-1 bg-gray-50 rounded text-xs text-gray-600">
          Контекст: {context}
        </div>
      )}
      {note && (
        <p className="text-xs text-gray-400 italic">{note}</p>
      )}
    </div>
  );
}

// Main Settings Modal Component
export default function SettingsModal() {
  const [isOpen, setIsOpen] = useState(true);
  
  // Settings state
  const [settings, setSettings] = useState({
    transcription: 'large-v3-turbo',
    cleaning: 'claude-sonnet-4.5',
    longread: 'claude-sonnet-4.5',
    summary: 'claude-sonnet-4.5',
  });
  
  const updateSetting = (key, value) => {
    setSettings(prev => ({ ...prev, [key]: value }));
  };
  
  const getModelInfo = (modelId, models) => {
    return models.find(m => m.id === modelId) || {};
  };
  
  const handleReset = () => {
    setSettings({
      transcription: 'large-v3-turbo',
      cleaning: 'claude-sonnet-4.5',
      longread: 'claude-sonnet-4.5',
      summary: 'claude-sonnet-4.5',
    });
  };
  
  const handleSave = () => {
    alert('Настройки сохранены!');
    setIsOpen(false);
  };
  
  const handleCancel = () => {
    setIsOpen(false);
  };

  if (!isOpen) {
    return (
      <div className="flex items-center justify-center h-screen bg-gray-100">
        <button
          onClick={() => setIsOpen(true)}
          className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600"
        >
          Открыть настройки
        </button>
      </div>
    );
  }

  const cleaningModel = getModelInfo(settings.cleaning, allLLMModels);
  const longreadModel = getModelInfo(settings.longread, allLLMModels);
  const summaryModel = getModelInfo(settings.summary, allLLMModels);
  const transcriptionModel = getModelInfo(settings.transcription, whisperModels);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/30">
      <div className="w-full max-w-lg bg-white rounded-2xl shadow-xl overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100">
          <h2 className="text-lg font-semibold text-gray-900">Настройки моделей</h2>
          <button
            onClick={handleCancel}
            className="p-1.5 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-lg transition-colors"
          >
            <Icons.X className="w-5 h-5" />
          </button>
        </div>
        
        {/* Content */}
        <div className="px-6 max-h-[60vh] overflow-y-auto">
          {/* Transcription */}
          <SettingsSection title="Транскрипция">
            <ModelSelect
              value={settings.transcription}
              onChange={(v) => updateSetting('transcription', v)}
              options={whisperModels}
              showCloudBadge={false}
            />
            <ModelInfo
              description={transcriptionModel.description}
              note="Использует настройки сервера"
            />
          </SettingsSection>
          
          {/* Cleaning */}
          <SettingsSection 
            title="Очистка" 
            badge={cleaningModel.type === 'cloud' ? 'Cloud' : undefined}
          >
            <ModelSelect
              value={settings.cleaning}
              onChange={(v) => updateSetting('cleaning', v)}
              options={allLLMModels}
            />
            <ModelInfo
              description={cleaningModel.description}
              context={cleaningModel.context}
              note="Использует настройки сервера"
            />
          </SettingsSection>
          
          {/* Longread */}
          <SettingsSection 
            title="Лонгрид" 
            badge={longreadModel.type === 'cloud' ? 'Cloud' : undefined}
          >
            <ModelSelect
              value={settings.longread}
              onChange={(v) => updateSetting('longread', v)}
              options={allLLMModels}
            />
            <ModelInfo
              description={longreadModel.description}
              context={longreadModel.context}
              note="Использует настройки сервера"
            />
          </SettingsSection>
          
          {/* Summary */}
          <SettingsSection 
            title="Конспект" 
            badge={summaryModel.type === 'cloud' ? 'Cloud' : undefined}
          >
            <ModelSelect
              value={settings.summary}
              onChange={(v) => updateSetting('summary', v)}
              options={allLLMModels}
            />
            <ModelInfo
              description={summaryModel.description}
              context={summaryModel.context}
              note="Использует настройки сервера"
            />
          </SettingsSection>
        </div>
        
        {/* Footer */}
        <div className="flex items-center justify-between px-6 py-4 bg-gray-50 border-t border-gray-100">
          <button
            onClick={handleReset}
            className="flex items-center gap-2 px-3 py-2 text-sm text-gray-600 hover:text-gray-800 hover:bg-gray-100 rounded-lg transition-colors"
          >
            <Icons.RefreshCw className="w-4 h-4" />
            Сбросить
          </button>
          
          <div className="flex items-center gap-3">
            <button
              onClick={handleCancel}
              className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
            >
              Отмена
            </button>
            <button
              onClick={handleSave}
              className="px-4 py-2 text-sm font-medium text-white bg-blue-500 rounded-lg hover:bg-blue-600 transition-colors"
            >
              Сохранить
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
