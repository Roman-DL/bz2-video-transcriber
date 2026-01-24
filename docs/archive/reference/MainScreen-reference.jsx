import { useState } from 'react';

// Inline SVG Icons
const Icons = {
  Music: ({ className }) => (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M9 18V5l12-2v13"/>
      <circle cx="6" cy="18" r="3"/>
      <circle cx="18" cy="16" r="3"/>
    </svg>
  ),
  Video: ({ className }) => (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="m22 8-6 4 6 4V8Z"/>
      <rect width="14" height="12" x="2" y="6" rx="2" ry="2"/>
    </svg>
  ),
  Folder: ({ className }) => (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M20 20a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-7.9a2 2 0 0 1-1.69-.9L9.6 3.9A2 2 0 0 0 7.93 3H4a2 2 0 0 0-2 2v13a2 2 0 0 0 2 2Z"/>
    </svg>
  ),
  FolderOpen: ({ className }) => (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="m6 14 1.5-2.9A2 2 0 0 1 9.24 10H20a2 2 0 0 1 1.94 2.5l-1.54 6a2 2 0 0 1-1.95 1.5H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h3.9a2 2 0 0 1 1.69.9l.81 1.2a2 2 0 0 0 1.67.9H18a2 2 0 0 1 2 2v2"/>
    </svg>
  ),
  FileText: ({ className }) => (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
      <polyline points="14 2 14 8 20 8"/>
      <line x1="16" y1="13" x2="8" y2="13"/>
      <line x1="16" y1="17" x2="8" y2="17"/>
    </svg>
  ),
  Play: ({ className }) => (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polygon points="5 3 19 12 5 21 5 3"/>
    </svg>
  ),
  Zap: ({ className }) => (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>
    </svg>
  ),
  ListOrdered: ({ className }) => (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <line x1="10" y1="6" x2="21" y2="6"/>
      <line x1="10" y1="12" x2="21" y2="12"/>
      <line x1="10" y1="18" x2="21" y2="18"/>
      <path d="M4 6h1v4"/>
      <path d="M4 10h2"/>
      <path d="M6 18H4c0-1 2-2 2-3s-1-1.5-2-1"/>
    </svg>
  ),
  Settings: ({ className }) => (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z"/>
      <circle cx="12" cy="12" r="3"/>
    </svg>
  ),
  RefreshCw: ({ className }) => (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="23 4 23 10 17 10"/>
      <polyline points="1 20 1 14 7 14"/>
      <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/>
    </svg>
  ),
  Inbox: ({ className }) => (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="22 12 16 12 14 15 10 15 8 12 2 12"/>
      <path d="M5.45 5.11 2 12v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6l-3.45-6.89A2 2 0 0 0 16.76 4H7.24a2 2 0 0 0-1.79 1.11z"/>
    </svg>
  ),
  Archive: ({ className }) => (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <rect width="20" height="5" x="2" y="3" rx="1"/>
      <path d="M4 8v11a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8"/>
      <path d="M10 12h4"/>
    </svg>
  ),
  ChevronRight: ({ className }) => (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="9 18 15 12 9 6"/>
    </svg>
  ),
  ChevronDown: ({ className }) => (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="6 9 12 15 18 9"/>
    </svg>
  ),
  Search: ({ className }) => (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="11" cy="11" r="8"/>
      <line x1="21" y1="21" x2="16.65" y2="16.65"/>
    </svg>
  ),
  Clock: ({ className }) => (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="10"/>
      <polyline points="12 6 12 12 16 14"/>
    </svg>
  ),
  Check: ({ className }) => (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="20 6 9 17 4 12"/>
    </svg>
  ),
};

// Status indicator component
function StatusDot({ status, label }) {
  const colors = {
    online: 'bg-emerald-500',
    offline: 'bg-gray-300',
    loading: 'bg-amber-500 animate-pulse',
  };
  
  return (
    <div className="flex items-center gap-1.5">
      <div className={`w-2 h-2 rounded-full ${colors[status]}`} />
      <span className="text-sm text-gray-600">{label}</span>
    </div>
  );
}

// Split button for process mode
function ProcessButton({ file, defaultMode, onProcess, onModeChange }) {
  const [isOpen, setIsOpen] = useState(false);
  
  const modes = [
    { 
      id: 'step', 
      name: 'Пошагово', 
      icon: Icons.ListOrdered,
      description: 'Контроль каждого этапа'
    },
    { 
      id: 'auto', 
      name: 'Авто', 
      icon: Icons.Zap,
      description: 'Все этапы без остановок'
    },
  ];
  
  const currentMode = modes.find(m => m.id === defaultMode) || modes[0];
  const CurrentIcon = currentMode.icon;
  
  return (
    <div className="relative">
      <div className="flex">
        {/* Main button */}
        <button
          onClick={() => onProcess(file, defaultMode)}
          className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-white bg-blue-500 rounded-l-lg hover:bg-blue-600 transition-colors"
        >
          <CurrentIcon className="w-3.5 h-3.5" />
          {currentMode.name}
        </button>
        
        {/* Dropdown trigger */}
        <button
          onClick={() => setIsOpen(!isOpen)}
          className="flex items-center px-1.5 py-1.5 text-white bg-blue-500 border-l border-blue-400 rounded-r-lg hover:bg-blue-600 transition-colors"
        >
          <Icons.ChevronDown className={`w-3.5 h-3.5 transition-transform ${isOpen ? 'rotate-180' : ''}`} />
        </button>
      </div>
      
      {/* Dropdown menu */}
      {isOpen && (
        <>
          <div 
            className="fixed inset-0 z-10" 
            onClick={() => setIsOpen(false)}
          />
          <div className="absolute right-0 z-20 mt-1 w-48 bg-white border border-gray-200 rounded-xl shadow-lg overflow-hidden">
            {modes.map((mode) => {
              const Icon = mode.icon;
              const isSelected = mode.id === defaultMode;
              return (
                <button
                  key={mode.id}
                  onClick={() => {
                    onModeChange(mode.id);
                    onProcess(file, mode.id);
                    setIsOpen(false);
                  }}
                  className={`w-full flex items-start gap-3 px-3 py-2.5 text-left hover:bg-gray-50 transition-colors ${
                    isSelected ? 'bg-blue-50' : ''
                  }`}
                >
                  <div className={`p-1.5 rounded-lg ${isSelected ? 'bg-blue-100 text-blue-600' : 'bg-gray-100 text-gray-500'}`}>
                    <Icon className="w-4 h-4" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className={`text-sm font-medium ${isSelected ? 'text-blue-600' : 'text-gray-900'}`}>
                        {mode.name}
                      </span>
                      {isSelected && (
                        <Icons.Check className="w-3.5 h-3.5 text-blue-500" />
                      )}
                    </div>
                    <p className="text-xs text-gray-500 mt-0.5">{mode.description}</p>
                  </div>
                </button>
              );
            })}
          </div>
        </>
      )}
    </div>
  );
}

// Inbox file card
function InboxCard({ file, defaultMode, onProcess, onModeChange }) {
  const isAudio = file.type === 'audio';
  const Icon = isAudio ? Icons.Music : Icons.Video;
  
  return (
    <div className="bg-white border border-gray-200 rounded-xl p-4 hover:border-blue-300 hover:shadow-md transition-all group">
      <div className="flex items-start gap-3 mb-3">
        <div className={`p-2 rounded-lg ${isAudio ? 'bg-violet-50 text-violet-500' : 'bg-sky-50 text-sky-500'}`}>
          <Icon className="w-5 h-5" />
        </div>
        <div className="flex-1 min-w-0">
          <h3 className="text-sm font-medium text-gray-900 leading-snug mb-1">
            {file.name}
          </h3>
          <p className="text-xs text-gray-400">
            {file.speaker}
          </p>
        </div>
      </div>
      
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3 text-xs text-gray-400">
          <span className="flex items-center gap-1">
            <Icons.Clock className="w-3 h-3" />
            {file.duration}
          </span>
          <span>{file.size}</span>
        </div>
        <ProcessButton
          file={file}
          defaultMode={defaultMode}
          onProcess={onProcess}
          onModeChange={onModeChange}
        />
      </div>
    </div>
  );
}

// Tree node component for archive
function TreeNode({ node, level = 0, onFileClick }) {
  const [isExpanded, setIsExpanded] = useState(level < 2);
  const isFolder = node.type === 'folder';
  const hasChildren = isFolder && node.children && node.children.length > 0;
  
  const paddingLeft = level * 16;
  
  return (
    <div>
      <div
        className={`flex items-center gap-2 py-1.5 px-2 rounded-lg cursor-pointer transition-colors ${
          isFolder ? 'hover:bg-gray-50' : 'hover:bg-blue-50'
        }`}
        style={{ paddingLeft: `${paddingLeft + 8}px` }}
        onClick={() => {
          if (isFolder) {
            setIsExpanded(!isExpanded);
          } else {
            onFileClick(node);
          }
        }}
      >
        {isFolder ? (
          <>
            <Icons.ChevronRight 
              className={`w-4 h-4 text-gray-400 transition-transform ${isExpanded ? 'rotate-90' : ''}`} 
            />
            {isExpanded ? (
              <Icons.FolderOpen className="w-4 h-4 text-amber-500" />
            ) : (
              <Icons.Folder className="w-4 h-4 text-amber-500" />
            )}
            <span className="text-sm font-medium text-gray-700">{node.name}</span>
            {node.count && (
              <span className="text-xs text-gray-400 ml-1">({node.count})</span>
            )}
          </>
        ) : (
          <>
            <div className="w-4" />
            <Icons.FileText className="w-4 h-4 text-gray-400" />
            <span className="text-sm text-gray-600 hover:text-blue-600 transition-colors">
              {node.name}
            </span>
            {node.speaker && (
              <span className="text-xs text-gray-400 ml-1">({node.speaker})</span>
            )}
          </>
        )}
      </div>
      
      {isFolder && isExpanded && hasChildren && (
        <div>
          {node.children.map((child, index) => (
            <TreeNode 
              key={index} 
              node={child} 
              level={level + 1} 
              onFileClick={onFileClick}
            />
          ))}
        </div>
      )}
    </div>
  );
}

// Sample data
const inboxFiles = [
  {
    id: 1,
    name: '2026.01 Форум Табтим. # Антоновы (Дмитрий и Юлия)',
    speaker: 'Дмитрий и Юлия Антоновы',
    type: 'audio',
    duration: '5:32',
    size: '48 MB',
  },
  {
    id: 2,
    name: '2026.01 Форум Табтим. Тестовая тема (Светлана Дмитрук)',
    speaker: 'Светлана Дмитрук',
    type: 'audio',
    duration: '3:15',
    size: '28 MB',
  },
];

const archiveTree = [
  {
    type: 'folder',
    name: '2025',
    count: 3,
    children: [
      {
        type: 'folder',
        name: '12.25 ПШ',
        count: 1,
        children: [
          { type: 'file', name: 'SV Закрытие ПО, возражения', speaker: 'Кухаренко Женя' },
        ],
      },
      {
        type: 'folder',
        name: '12.22 ПШ',
        count: 2,
        children: [
          { type: 'file', name: 'SV Закрытие ПО, возражения', speaker: 'Кухаренко Женя' },
          { type: 'file', name: 'SV Тестовая запись', speaker: 'Тест' },
        ],
      },
    ],
  },
  {
    type: 'folder',
    name: '2026',
    count: 1,
    children: [
      {
        type: 'folder',
        name: 'ПШ',
        count: 1,
        children: [
          { type: 'file', name: '01.22' },
        ],
      },
    ],
  },
];

export default function MainScreen() {
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedFile, setSelectedFile] = useState(null);
  const [defaultMode, setDefaultMode] = useState('step'); // 'step' для отладки, потом 'auto'
  
  const handleProcess = (file, mode) => {
    if (mode === 'step') {
      alert(`Открываем ПОШАГОВЫЙ режим для:\n${file.name}`);
    } else {
      alert(`Запускаем АВТОМАТИЧЕСКУЮ обработку:\n${file.name}`);
    }
  };
  
  const handleModeChange = (mode) => {
    setDefaultMode(mode);
  };
  
  const handleFileClick = (file) => {
    setSelectedFile(file);
    alert(`Открываем результаты для: ${file.name}`);
  };
  
  const handleSettings = () => {
    alert('Открываем настройки');
  };
  
  const handleRefresh = (section) => {
    alert(`Обновляем ${section}`);
  };

  return (
    <div className="flex flex-col h-screen bg-stone-50">
      {/* Header */}
      <header className="flex items-center justify-between px-6 py-4 bg-white border-b border-gray-200">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-gradient-to-br from-blue-500 to-blue-600 rounded-lg">
            <Icons.Video className="w-5 h-5 text-white" />
          </div>
          <div>
            <h1 className="text-lg font-semibold text-gray-900">БЗ Транскрибатор</h1>
            <span className="text-xs text-gray-400">v0.37.0 • 22.01.26 09:25</span>
          </div>
        </div>
        
        <div className="flex items-center gap-6">
          <div className="flex items-center gap-4">
            <StatusDot status="online" label="Whisper" />
            <StatusDot status="online" label="Ollama" />
          </div>
          <button
            onClick={handleSettings}
            className="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-lg transition-colors"
          >
            <Icons.Settings className="w-5 h-5" />
          </button>
        </div>
      </header>

      {/* Main content */}
      <div className="flex flex-1 overflow-hidden">
        {/* Left Panel - Inbox */}
        <aside className="w-80 flex flex-col bg-white border-r border-gray-200">
          {/* Inbox Header */}
          <div className="flex items-center justify-between px-4 py-3 border-b border-gray-100">
            <div className="flex items-center gap-2">
              <Icons.Inbox className="w-5 h-5 text-gray-400" />
              <h2 className="font-medium text-gray-900">Inbox</h2>
              <span className="text-xs font-medium text-gray-400 bg-gray-100 px-2 py-0.5 rounded-full">
                {inboxFiles.length}
              </span>
            </div>
            <button
              onClick={() => handleRefresh('inbox')}
              className="p-1.5 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-lg transition-colors"
            >
              <Icons.RefreshCw className="w-4 h-4" />
            </button>
          </div>
          
          {/* Current mode indicator */}
          <div className="px-4 py-2 bg-gray-50 border-b border-gray-100">
            <div className="flex items-center gap-2 text-xs text-gray-500">
              <span>Режим по умолчанию:</span>
              <span className={`font-medium ${defaultMode === 'step' ? 'text-blue-600' : 'text-emerald-600'}`}>
                {defaultMode === 'step' ? 'Пошагово' : 'Авто'}
              </span>
            </div>
          </div>
          
          {/* Inbox Files */}
          <div className="flex-1 p-4 space-y-3 overflow-y-auto">
            {inboxFiles.length > 0 ? (
              inboxFiles.map((file) => (
                <InboxCard 
                  key={file.id} 
                  file={file} 
                  defaultMode={defaultMode}
                  onProcess={handleProcess}
                  onModeChange={handleModeChange}
                />
              ))
            ) : (
              <div className="flex flex-col items-center justify-center h-full text-gray-400">
                <Icons.Inbox className="w-12 h-12 mb-3 opacity-40" />
                <p className="text-sm">Нет файлов для обработки</p>
              </div>
            )}
          </div>
        </aside>

        {/* Right Panel - Archive */}
        <main className="flex-1 flex flex-col bg-stone-50">
          {/* Archive Header */}
          <div className="flex items-center justify-between px-5 py-3 bg-white border-b border-gray-200">
            <div className="flex items-center gap-2">
              <Icons.Archive className="w-5 h-5 text-gray-400" />
              <h2 className="font-medium text-gray-900">Архив</h2>
              <span className="text-xs font-medium text-gray-400 bg-gray-100 px-2 py-0.5 rounded-full">
                4 видео
              </span>
            </div>
            <div className="flex items-center gap-2">
              {/* Search */}
              <div className="relative">
                <Icons.Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                <input
                  type="text"
                  placeholder="Поиск..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-9 pr-4 py-2 w-64 text-sm bg-gray-50 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-100 focus:border-blue-500 transition-colors"
                />
              </div>
              <button
                onClick={() => handleRefresh('archive')}
                className="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-lg transition-colors"
              >
                <Icons.RefreshCw className="w-4 h-4" />
              </button>
            </div>
          </div>
          
          {/* Archive Tree */}
          <div className="flex-1 p-4 overflow-y-auto">
            <div className="bg-white border border-gray-200 rounded-xl p-3">
              {archiveTree.map((node, index) => (
                <TreeNode 
                  key={index} 
                  node={node} 
                  onFileClick={handleFileClick}
                />
              ))}
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}
