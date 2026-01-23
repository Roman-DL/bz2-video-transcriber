import { useState } from 'react';

// ============================================================================
// ICONS
// ============================================================================
const Icons = {
  Clock: ({ className }) => <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>,
  FileText: ({ className }) => <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/></svg>,
  AudioLines: ({ className }) => <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M2 10v3"/><path d="M6 6v11"/><path d="M10 3v18"/><path d="M14 8v7"/><path d="M18 5v13"/><path d="M22 10v3"/></svg>,
  Sparkles: ({ className }) => <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="m12 3-1.912 5.813a2 2 0 0 1-1.275 1.275L3 12l5.813 1.912a2 2 0 0 1 1.275 1.275L12 21l1.912-5.813a2 2 0 0 1 1.275-1.275L21 12l-5.813-1.912a2 2 0 0 1-1.275-1.275L12 3Z"/></svg>,
  Layers: ({ className }) => <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polygon points="12 2 2 7 12 12 22 7 12 2"/><polyline points="2 17 12 22 22 17"/><polyline points="2 12 12 17 22 12"/></svg>,
  BookOpen: ({ className }) => <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"/><path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"/></svg>,
  ListTree: ({ className }) => <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 12h-8"/><path d="M21 6H8"/><path d="M21 18h-8"/><path d="M3 6v4c0 1.1.9 2 2 2h3"/><path d="M3 10v6c0 1.1.9 2 2 2h3"/></svg>,
  Image: ({ className }) => <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect width="18" height="18" x="3" y="3" rx="2"/><circle cx="9" cy="9" r="2"/><path d="m21 15-3.086-3.086a2 2 0 0 0-2.828 0L6 21"/></svg>,
  BarChart3: ({ className }) => <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M3 3v18h18"/><path d="M18 17V9"/><path d="M13 17V5"/><path d="M8 17v-3"/></svg>,
  Coins: ({ className }) => <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="8" cy="8" r="6"/><path d="M18.09 10.37A6 6 0 1 1 10.34 18"/><path d="M7 6h1v4"/><path d="m16.71 13.88.7.71-2.82 2.82"/></svg>,
  Cloud: ({ className }) => <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M17.5 19H9a7 7 0 1 1 6.71-9h1.79a4.5 4.5 0 1 1 0 9Z"/></svg>,
  Server: ({ className }) => <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect width="20" height="8" x="2" y="2" rx="2" ry="2"/><rect width="20" height="8" x="2" y="14" rx="2" ry="2"/><line x1="6" y1="6" x2="6.01" y2="6"/><line x1="6" y1="18" x2="6.01" y2="18"/></svg>,
  Save: ({ className }) => <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/><polyline points="17 21 17 13 7 13 7 21"/><polyline points="7 3 7 8 15 8"/></svg>,
  CheckCircle: ({ className }) => <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>,
  Calendar: ({ className }) => <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect width="18" height="18" x="3" y="4" rx="2" ry="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>,
  File: ({ className }) => <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>,
  ArrowLeft: ({ className }) => <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="19" y1="12" x2="5" y2="12"/><polyline points="12 19 5 12 12 5"/></svg>,
  Check: ({ className }) => <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="20 6 9 17 4 12"/></svg>,
  Circle: ({ className }) => <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="10"/></svg>,
};

// ============================================================================
// MOCK DATA
// ============================================================================
const PROCESSING_STATS = {
  processedAt: '2026-01-22 14:35:22',
  totalTime: '1м 45с',
  fileName: '2026.01 Форум Табтим. Тестовая тема (Светлана Дмитрук).mp3',
  slidesCount: 1,
  steps: [
    { 
      id: 'parse', 
      name: 'Парсинг метаданных', 
      icon: 'FileText',
      time: '0.1с',
      model: null,
      tokens: null,
      cost: null,
    },
    { 
      id: 'transcribe', 
      name: 'Транскрипция', 
      icon: 'AudioLines',
      time: '23с',
      model: 'large-v3-turbo',
      modelType: 'local',
      tokens: null,
      cost: null,
      outputChars: 4188,
      outputWords: 662,
    },
    { 
      id: 'clean', 
      name: 'Очистка текста', 
      icon: 'Sparkles',
      time: '20с',
      model: 'claude-sonnet-4-5',
      modelType: 'cloud',
      tokens: { input: 23280, output: 1833 },
      cost: 0.097,
      outputChars: 3980,
      outputWords: 628,
    },
    { 
      id: 'slides', 
      name: 'Извлечение слайдов', 
      icon: 'Image',
      time: '7с',
      model: 'claude-haiku-4-5',
      modelType: 'cloud',
      tokens: { input: 1919, output: 490 },
      cost: 0.0044,
      outputChars: 1064,
      outputWords: 162,
      slidesCount: 1,
    },
    { 
      id: 'longread', 
      name: 'Генерация лонгрида', 
      icon: 'BookOpen',
      time: '35с',
      model: 'claude-sonnet-4-5',
      modelType: 'cloud',
      tokens: { input: 28450, output: 3240 },
      cost: 0.134,
      outputChars: 12840,
      outputWords: 1856,
    },
    { 
      id: 'summary', 
      name: 'Генерация конспекта', 
      icon: 'ListTree',
      time: '18с',
      model: 'claude-sonnet-4-5',
      modelType: 'cloud',
      tokens: { input: 8420, output: 1250 },
      cost: 0.044,
      outputChars: 4920,
      outputWords: 687,
    },
    { 
      id: 'chunk', 
      name: 'Разбиение на чанки', 
      icon: 'Layers',
      time: '0.2с',
      model: null,
      tokens: null,
      cost: null,
      chunksCount: 8,
      totalTokens: 2840,
    },
    { 
      id: 'save', 
      name: 'Сохранение в архив', 
      icon: 'Save',
      time: '1.2с',
      model: null,
      tokens: null,
      cost: null,
      filesCount: 8,
    },
  ],
  files: [
    { name: 'pipeline_results.json', size: '12.4 KB' },
    { name: 'transcript_chunks.json', size: '8.2 KB' },
    { name: 'longread.md', size: '4.1 KB' },
    { name: 'summary.md', size: '2.8 KB' },
    { name: 'transcript_raw.txt', size: '4.4 KB' },
    { name: 'transcript_cleaned.txt', size: '4.2 KB' },
    { name: 'slides_extracted.md', size: '1.8 KB' },
    { name: 'audio.mp3', size: '12.4 MB' },
  ],
  totals: {
    inputTokens: 62069,
    outputTokens: 6813,
    cost: 0.279,
  }
};

// ============================================================================
// HELPER FUNCTIONS
// ============================================================================
function formatCost(cost) {
  if (!cost) return '—';
  if (cost < 0.01) return `$${cost.toFixed(4)}`;
  return `$${cost.toFixed(2)}`;
}

// ============================================================================
// STATISTICS TAB CONTENT
// ============================================================================
function StatisticsTabContent() {
  const stats = PROCESSING_STATS;
  
  return (
    <div className="flex flex-col h-full bg-white rounded-xl border border-stone-200 overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-5 py-4 bg-stone-50 border-b border-stone-100">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-violet-500 to-purple-600 flex items-center justify-center">
            <Icons.BarChart3 className="w-5 h-5 text-white" />
          </div>
          <div>
            <h3 className="text-base font-semibold text-stone-900">Статистика обработки</h3>
            <div className="flex items-center gap-2 text-xs text-stone-500">
              <Icons.Calendar className="w-3.5 h-3.5" />
              <span>{stats.processedAt}</span>
            </div>
          </div>
        </div>
      </div>
      
      {/* Content */}
      <div className="flex-1 p-5 overflow-y-auto space-y-6">
        {/* Summary Cards */}
        <div className="grid grid-cols-3 gap-4">
          <div className="p-4 bg-gradient-to-br from-blue-50 to-indigo-50 rounded-xl border border-blue-100">
            <div className="flex items-center gap-2 mb-2">
              <Icons.Clock className="w-4 h-4 text-blue-600" />
              <span className="text-xs font-medium text-blue-600 uppercase tracking-wide">Общее время</span>
            </div>
            <div className="text-2xl font-bold text-stone-900">{stats.totalTime}</div>
          </div>
          
          <div className="p-4 bg-gradient-to-br from-violet-50 to-purple-50 rounded-xl border border-violet-100">
            <div className="flex items-center gap-2 mb-2">
              <Icons.Sparkles className="w-4 h-4 text-violet-600" />
              <span className="text-xs font-medium text-violet-600 uppercase tracking-wide">Токены</span>
            </div>
            <div className="flex items-baseline gap-2">
              <span className="text-xl font-bold text-stone-900">{stats.totals.inputTokens.toLocaleString()}</span>
              <span className="text-xs text-stone-500">вх.</span>
              <span className="text-stone-300">/</span>
              <span className="text-xl font-bold text-stone-900">{stats.totals.outputTokens.toLocaleString()}</span>
              <span className="text-xs text-stone-500">вых.</span>
            </div>
          </div>
          
          <div className="p-4 bg-gradient-to-br from-emerald-50 to-teal-50 rounded-xl border border-emerald-100">
            <div className="flex items-center gap-2 mb-2">
              <Icons.Coins className="w-4 h-4 text-emerald-600" />
              <span className="text-xs font-medium text-emerald-600 uppercase tracking-wide">Стоимость</span>
            </div>
            <div className="text-2xl font-bold text-stone-900">${stats.totals.cost.toFixed(2)}</div>
          </div>
        </div>
        
        {/* Steps Breakdown */}
        <div>
          <h4 className="text-sm font-semibold text-stone-700 mb-3">Детализация по этапам</h4>
          <div className="bg-white border border-stone-200 rounded-xl overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-stone-50 border-b border-stone-200">
                  <th className="text-left px-4 py-2.5 font-medium text-stone-500 text-xs uppercase tracking-wide">Этап</th>
                  <th className="text-left px-4 py-2.5 font-medium text-stone-500 text-xs uppercase tracking-wide">Модель</th>
                  <th className="text-right px-4 py-2.5 font-medium text-stone-500 text-xs uppercase tracking-wide">Время</th>
                  <th className="text-right px-4 py-2.5 font-medium text-stone-500 text-xs uppercase tracking-wide">Токены</th>
                  <th className="text-right px-4 py-2.5 font-medium text-stone-500 text-xs uppercase tracking-wide">Стоимость</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-stone-100">
                {stats.steps.map((step) => {
                  const Icon = Icons[step.icon];
                  const hasLLM = step.model && step.modelType === 'cloud';
                  return (
                    <tr key={step.id} className="hover:bg-stone-50/50 transition-colors">
                      <td className="px-4 py-2.5">
                        <div className="flex items-center gap-2">
                          <div className={`w-6 h-6 rounded-lg flex items-center justify-center ${
                            hasLLM ? 'bg-violet-100' : 'bg-stone-100'
                          }`}>
                            <Icon className={`w-3.5 h-3.5 ${hasLLM ? 'text-violet-600' : 'text-stone-500'}`} />
                          </div>
                          <span className="text-stone-900 font-medium">{step.name}</span>
                        </div>
                      </td>
                      <td className="px-4 py-2.5">
                        {step.model ? (
                          <div className="flex items-center gap-1.5">
                            {step.modelType === 'cloud' ? (
                              <Icons.Cloud className="w-3.5 h-3.5 text-violet-500" />
                            ) : (
                              <Icons.Server className="w-3.5 h-3.5 text-emerald-500" />
                            )}
                            <span className="font-mono text-xs text-stone-600">{step.model}</span>
                          </div>
                        ) : (
                          <span className="text-stone-300">—</span>
                        )}
                      </td>
                      <td className="px-4 py-2.5 text-right">
                        <span className="text-emerald-600 font-medium">{step.time}</span>
                      </td>
                      <td className="px-4 py-2.5 text-right font-mono text-xs">
                        {step.tokens ? (
                          <span className="text-stone-600">
                            {step.tokens.input.toLocaleString()} / {step.tokens.output.toLocaleString()}
                          </span>
                        ) : (
                          <span className="text-stone-300">—</span>
                        )}
                      </td>
                      <td className="px-4 py-2.5 text-right">
                        {step.cost ? (
                          <span className="text-violet-600 font-semibold">{formatCost(step.cost)}</span>
                        ) : (
                          <span className="text-stone-300">—</span>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
              <tfoot>
                <tr className="bg-stone-100 border-t-2 border-stone-200">
                  <td className="px-4 py-3 font-semibold text-stone-900">Итого</td>
                  <td className="px-4 py-3"></td>
                  <td className="px-4 py-3 text-right font-semibold text-emerald-600">{stats.totalTime}</td>
                  <td className="px-4 py-3 text-right font-mono text-xs font-semibold text-stone-900">
                    {stats.totals.inputTokens.toLocaleString()} / {stats.totals.outputTokens.toLocaleString()}
                  </td>
                  <td className="px-4 py-3 text-right font-semibold text-violet-600">
                    ${stats.totals.cost.toFixed(2)}
                  </td>
                </tr>
              </tfoot>
            </table>
          </div>
        </div>
        
        {/* Files Created */}
        <div>
          <h4 className="text-sm font-semibold text-stone-700 mb-3">Созданные файлы</h4>
          <div className="grid grid-cols-2 gap-2">
            {stats.files.map((file, idx) => (
              <div 
                key={idx} 
                className="flex items-center justify-between px-3 py-2 bg-stone-50 rounded-lg border border-stone-100"
              >
                <div className="flex items-center gap-2">
                  <Icons.File className="w-4 h-4 text-stone-400" />
                  <span className="font-mono text-xs text-stone-700">{file.name}</span>
                </div>
                <span className="text-xs text-stone-400">{file.size}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

// ============================================================================
// COMPACT SAVE SUCCESS CARD (для левой панели)
// ============================================================================
function CompactSaveSuccessCard({ onClose }) {
  return (
    <div className="p-4 bg-gradient-to-br from-emerald-50 to-teal-50 border border-emerald-200 rounded-xl">
      <div className="flex items-center gap-3 mb-3">
        <div className="w-9 h-9 flex items-center justify-center bg-emerald-500 rounded-xl">
          <Icons.CheckCircle className="w-5 h-5 text-white" />
        </div>
        <div>
          <h3 className="text-sm font-semibold text-stone-900">Успешно сохранено</h3>
          <p className="text-xs text-stone-500">{PROCESSING_STATS.files.length} файлов</p>
        </div>
      </div>
      
      {/* Compact file list */}
      <div className="space-y-1 mb-3 max-h-32 overflow-y-auto">
        {PROCESSING_STATS.files.map((file, idx) => (
          <div 
            key={idx} 
            className="flex items-center justify-between px-2 py-1.5 bg-white/60 rounded text-xs"
          >
            <span className="font-mono text-stone-600 truncate">{file.name}</span>
            <span className="text-stone-400 ml-2 flex-shrink-0">{file.size}</span>
          </div>
        ))}
      </div>
      
      <button 
        onClick={onClose}
        className="w-full px-4 py-2.5 text-sm font-semibold text-white bg-emerald-600 rounded-lg hover:bg-emerald-700 transition-colors"
      >
        Закрыть
      </button>
    </div>
  );
}

// ============================================================================
// STEPS TIMELINE (левая панель)
// ============================================================================
function StepsTimeline({ currentStep }) {
  const steps = PROCESSING_STATS.steps;
  
  return (
    <div className="flex-1 overflow-y-auto">
      <h4 className="text-xs font-semibold uppercase tracking-wider text-stone-400 mb-3 px-1">
        Этапы обработки
      </h4>
      <div className="space-y-0.5">
        {steps.map((step, index) => {
          const Icon = Icons[step.icon];
          const isCompleted = index < steps.findIndex(s => s.id === currentStep);
          const isCurrent = step.id === currentStep;
          const isPending = !isCompleted && !isCurrent;
          
          return (
            <div 
              key={step.id}
              className={`flex items-center gap-3 px-3 py-2 rounded-lg transition-colors ${
                isCurrent ? 'bg-emerald-50 border border-emerald-200' : 
                isCompleted ? 'hover:bg-stone-50' : ''
              }`}
            >
              {/* Status icon */}
              <div className="relative flex flex-col items-center">
                {isCompleted ? (
                  <Icons.CheckCircle className="w-5 h-5 text-emerald-500" />
                ) : isCurrent ? (
                  <div className="w-5 h-5 rounded-full bg-emerald-500 flex items-center justify-center">
                    <Icons.Check className="w-3 h-3 text-white" />
                  </div>
                ) : (
                  <Icons.Circle className="w-5 h-5 text-stone-300" />
                )}
                {index < steps.length - 1 && (
                  <div className={`absolute top-6 left-1/2 -translate-x-1/2 w-0.5 h-5 ${
                    isCompleted ? 'bg-emerald-500' : 'bg-stone-200'
                  }`} />
                )}
              </div>
              
              {/* Step info */}
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <Icon className={`w-4 h-4 ${
                    isCurrent ? 'text-emerald-600' : 
                    isCompleted ? 'text-stone-500' : 'text-stone-300'
                  }`} />
                  <span className={`text-sm font-medium truncate ${
                    isCurrent ? 'text-emerald-700' : 
                    isCompleted ? 'text-stone-900' : 'text-stone-400'
                  }`}>
                    {step.name}
                  </span>
                  {isCurrent && (
                    <span className="px-1.5 py-0.5 bg-emerald-100 text-emerald-700 text-[10px] font-bold uppercase tracking-wide rounded">
                      текущий
                    </span>
                  )}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ============================================================================
// TABS
// ============================================================================
const TABS = [
  { id: 'metadata', label: 'Метаданные', icon: 'FileText' },
  { id: 'transcript', label: 'Транскрипт', icon: 'AudioLines' },
  { id: 'clean', label: 'Очистка', icon: 'Sparkles' },
  { id: 'slides', label: 'Слайды', icon: 'Image' },
  { id: 'longread', label: 'Лонгрид', icon: 'BookOpen' },
  { id: 'summary', label: 'Конспект', icon: 'ListTree' },
  { id: 'chunks', label: 'Чанки', icon: 'Layers' },
  { id: 'stats', label: 'Статистика', icon: 'BarChart3' },
];

// ============================================================================
// MAIN DEMO
// ============================================================================
export default function StatisticsTabDemo() {
  const [activeTab, setActiveTab] = useState('stats');
  
  return (
    <div className="min-h-screen bg-stone-100">
      {/* Header */}
      <header className="flex items-center justify-between px-6 py-4 bg-white border-b border-stone-200">
        <div className="flex items-center gap-4">
          <button className="p-2 text-stone-400 hover:text-stone-600 hover:bg-stone-100 rounded-lg">
            <Icons.ArrowLeft className="w-5 h-5" />
          </button>
          <div>
            <span className="text-xs font-semibold uppercase tracking-wider text-stone-400">
              Пошаговая обработка
            </span>
            <h1 className="text-base font-medium text-stone-900 truncate max-w-lg">
              {PROCESSING_STATS.fileName}
            </h1>
          </div>
        </div>
        <button className="px-4 py-2 text-sm font-medium text-stone-600 border border-stone-300 rounded-lg hover:bg-stone-50">
          Отменить
        </button>
      </header>
      
      {/* Content */}
      <div className="flex h-[calc(100vh-65px)]">
        {/* Left Panel */}
        <aside className="w-80 flex flex-col gap-4 p-4 bg-white border-r border-stone-200 overflow-y-auto">
          {/* Success Card */}
          <CompactSaveSuccessCard onClose={() => alert('Закрыть')} />
          
          {/* Steps Timeline */}
          <StepsTimeline currentStep="save" />
        </aside>
        
        {/* Right Panel */}
        <main className="flex-1 flex flex-col overflow-hidden">
          {/* Tabs */}
          <div className="flex gap-1 px-5 py-3 bg-white border-b border-stone-200 overflow-x-auto">
            {TABS.map(tab => {
              const Icon = Icons[tab.icon];
              const isStats = tab.id === 'stats';
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium rounded-lg whitespace-nowrap transition-colors ${
                    activeTab === tab.id
                      ? isStats 
                        ? 'text-violet-600 bg-violet-50 border border-violet-200'
                        : 'text-blue-600 bg-blue-50 border border-blue-200'
                      : 'text-stone-500 hover:text-stone-700 hover:bg-stone-50 border border-transparent'
                  }`}
                >
                  <Icon className="w-4 h-4" />
                  {tab.label}
                </button>
              );
            })}
          </div>
          
          {/* Tab Content */}
          <div className="flex-1 p-5 overflow-hidden">
            {activeTab === 'stats' ? (
              <StatisticsTabContent />
            ) : (
              <div className="h-full bg-white rounded-xl border border-stone-200 flex items-center justify-center text-stone-400">
                <div className="text-center">
                  <Icons.FileText className="w-12 h-12 mx-auto mb-3 opacity-30" />
                  <p>Содержимое вкладки "{TABS.find(t => t.id === activeTab)?.label}"</p>
                </div>
              </div>
            )}
          </div>
        </main>
      </div>
    </div>
  );
}
