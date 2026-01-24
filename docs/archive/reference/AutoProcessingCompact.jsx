import { useState, useEffect } from 'react';

// ============================================================================
// ICONS
// ============================================================================
const Icons = {
  Check: ({ className }) => (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="20 6 9 17 4 12"/>
    </svg>
  ),
  Loader: ({ className }) => (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M21 12a9 9 0 1 1-6.219-8.56"/>
    </svg>
  ),
  Circle: ({ className }) => (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <circle cx="12" cy="12" r="10"/>
    </svg>
  ),
  X: ({ className }) => (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
    </svg>
  ),
  CheckCircle: ({ className }) => (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/>
    </svg>
  ),
  AlertCircle: ({ className }) => (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/>
    </svg>
  ),
  FolderOpen: ({ className }) => (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="m6 14 1.5-2.9A2 2 0 0 1 9.24 10H20a2 2 0 0 1 1.94 2.5l-1.54 6a2 2 0 0 1-1.95 1.5H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h3.9a2 2 0 0 1 1.69.9l.81 1.2a2 2 0 0 0 1.67.9H18a2 2 0 0 1 2 2v2"/>
    </svg>
  ),
};

// ============================================================================
// STEPS DATA
// ============================================================================
const STEPS = [
  { id: 'parse', label: 'Парсинг метаданных' },
  { id: 'transcribe', label: 'Транскрипция (Whisper)' },
  { id: 'clean', label: 'Очистка текста' },
  { id: 'slides', label: 'Извлечение слайдов' },
  { id: 'longread', label: 'Генерация лонгрида' },
  { id: 'summarize', label: 'Генерация конспекта' },
  { id: 'chunk', label: 'Разбиение на чанки' },
  { id: 'save', label: 'Сохранение в архив' },
];

const STEPS_NO_SLIDES = STEPS.filter(s => s.id !== 'slides');

// ============================================================================
// STEP ITEM COMPONENT
// ============================================================================
function StepItem({ step, status, isLast }) {
  const getIcon = () => {
    switch (status) {
      case 'completed':
        return (
          <div className="w-5 h-5 rounded-full bg-emerald-500 flex items-center justify-center">
            <Icons.Check className="w-3 h-3 text-white" />
          </div>
        );
      case 'running':
        return (
          <div className="w-5 h-5 rounded-full bg-blue-500 flex items-center justify-center">
            <Icons.Loader className="w-3 h-3 text-white animate-spin" />
          </div>
        );
      case 'error':
        return (
          <div className="w-5 h-5 rounded-full bg-red-500 flex items-center justify-center">
            <Icons.X className="w-3 h-3 text-white" />
          </div>
        );
      default:
        return (
          <div className="w-5 h-5 rounded-full border-2 border-stone-300" />
        );
    }
  };

  return (
    <div className="flex items-center gap-3 py-1.5">
      {/* Icon with connector line */}
      <div className="relative flex flex-col items-center">
        {getIcon()}
        {!isLast && (
          <div className={`absolute top-5 w-0.5 h-4 ${
            status === 'completed' ? 'bg-emerald-500' : 'bg-stone-200'
          }`} />
        )}
      </div>
      
      {/* Label */}
      <span className={`text-sm ${
        status === 'completed' ? 'text-stone-700' :
        status === 'running' ? 'text-blue-600 font-medium' :
        status === 'error' ? 'text-red-600' :
        'text-stone-400'
      }`}>
        {step.label}
      </span>
    </div>
  );
}

// ============================================================================
// PROGRESS HEADER COMPONENT
// ============================================================================
function ProgressHeader({ currentStep, totalSteps, stepLabel, progress, timeRemaining, status }) {
  if (status === 'completed') {
    return (
      <div className="flex items-center gap-3 py-3">
        <div className="w-10 h-10 rounded-full bg-emerald-100 flex items-center justify-center">
          <Icons.CheckCircle className="w-6 h-6 text-emerald-600" />
        </div>
        <div>
          <div className="text-sm font-medium text-emerald-600">УСПЕШНО ЗАВЕРШЕНО</div>
          <div className="text-xs text-stone-500">Все этапы выполнены</div>
        </div>
      </div>
    );
  }

  if (status === 'error') {
    return (
      <div className="flex items-center gap-3 py-3">
        <div className="w-10 h-10 rounded-full bg-red-100 flex items-center justify-center">
          <Icons.AlertCircle className="w-6 h-6 text-red-600" />
        </div>
        <div>
          <div className="text-sm font-medium text-red-600">ОШИБКА</div>
          <div className="text-xs text-stone-500">{stepLabel}</div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-full bg-blue-100 flex items-center justify-center">
          <Icons.Loader className="w-5 h-5 text-blue-600 animate-spin" />
        </div>
        <div className="flex-1">
          <div className="text-xs font-medium text-blue-600 uppercase tracking-wide">Выполняется</div>
          <div className="text-sm text-stone-900">{stepLabel} ({currentStep}/{totalSteps})</div>
        </div>
        <div className="text-xs text-stone-400">{timeRemaining}</div>
      </div>
      
      {/* Progress bar */}
      <div className="flex items-center gap-3">
        <div className="flex-1 h-1.5 bg-stone-200 rounded-full overflow-hidden">
          <div 
            className="h-full bg-blue-500 rounded-full transition-all duration-300"
            style={{ width: `${progress}%` }}
          />
        </div>
        <span className="text-xs text-stone-500 w-10 text-right">{progress}%</span>
      </div>
    </div>
  );
}

// ============================================================================
// MAIN COMPONENT: AutoProcessingModal
// ============================================================================
function AutoProcessingModal({ 
  fileName, 
  hasSlides = true,
  onCancel, 
  onOpenArchive 
}) {
  const [status, setStatus] = useState('running'); // running | completed | error
  const [currentStepIndex, setCurrentStepIndex] = useState(0);
  const [progress, setProgress] = useState(0);
  
  const steps = hasSlides ? STEPS : STEPS_NO_SLIDES;
  const currentStep = steps[currentStepIndex];
  
  // Simulate progress
  useEffect(() => {
    if (status !== 'running') return;
    
    const interval = setInterval(() => {
      setProgress(prev => {
        if (prev >= 100) {
          // Move to next step
          if (currentStepIndex < steps.length - 1) {
            setCurrentStepIndex(i => i + 1);
            return 0;
          } else {
            setStatus('completed');
            return 100;
          }
        }
        return prev + Math.random() * 15;
      });
    }, 400);
    
    return () => clearInterval(interval);
  }, [status, currentStepIndex, steps.length]);
  
  const getStepStatus = (index) => {
    if (index < currentStepIndex) return 'completed';
    if (index === currentStepIndex) return status === 'error' ? 'error' : 'running';
    return 'pending';
  };

  return (
    <div className="w-full max-w-md bg-white rounded-2xl shadow-xl overflow-hidden border border-stone-200">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 bg-stone-50 border-b border-stone-200">
        <span className="text-xs font-medium text-stone-500 uppercase tracking-wide">
          Автоматическая обработка
        </span>
        {status === 'running' && (
          <button 
            onClick={onCancel}
            className="px-3 py-1 text-xs font-medium text-stone-500 hover:text-stone-700 hover:bg-stone-200 rounded-lg transition-colors"
          >
            Отменить
          </button>
        )}
      </div>
      
      {/* File name */}
      <div className="px-4 py-2 border-b border-stone-100">
        <p className="text-sm font-medium text-stone-900 truncate" title={fileName}>
          {fileName}
        </p>
      </div>
      
      {/* Progress section */}
      <div className="px-4 py-3 border-b border-stone-100">
        <ProgressHeader
          currentStep={currentStepIndex + 1}
          totalSteps={steps.length}
          stepLabel={currentStep?.label}
          progress={Math.round(progress)}
          timeRemaining="менее 5 сек"
          status={status}
        />
      </div>
      
      {/* Steps list */}
      <div className="px-4 py-2 max-h-64 overflow-y-auto">
        {steps.map((step, index) => (
          <StepItem
            key={step.id}
            step={step}
            status={getStepStatus(index)}
            isLast={index === steps.length - 1}
          />
        ))}
      </div>
      
      {/* Footer - only show when completed */}
      {status === 'completed' && (
        <div className="px-4 py-3 bg-stone-50 border-t border-stone-200">
          <button
            onClick={onOpenArchive}
            className="w-full flex items-center justify-center gap-2 px-4 py-2 text-sm font-medium text-white bg-blue-500 rounded-lg hover:bg-blue-600 transition-colors"
          >
            <Icons.FolderOpen className="w-4 h-4" />
            Открыть в архиве
          </button>
        </div>
      )}
    </div>
  );
}

// ============================================================================
// COMPARISON: OLD VS NEW
// ============================================================================
function OldDesignMock() {
  return (
    <div className="w-full max-w-md bg-white rounded-2xl shadow-xl overflow-hidden border border-stone-200 text-xs text-stone-400 p-4">
      <div className="text-center mb-4">
        <div className="text-sm font-medium text-stone-900 mb-1">Старый дизайн</div>
        <div className="text-stone-500">~500px высота</div>
      </div>
      <div className="space-y-4 opacity-50">
        <div className="h-8 bg-stone-100 rounded" />
        <div className="h-6 bg-stone-100 rounded w-3/4" />
        <div className="h-20 bg-stone-100 rounded" />
        <div className="space-y-3">
          {[1,2,3,4,5,6,7,8].map(i => (
            <div key={i} className="h-8 bg-stone-100 rounded flex items-center px-3 gap-2">
              <div className="w-5 h-5 rounded-full bg-stone-200" />
              <div className="flex-1 h-3 bg-stone-200 rounded" />
              <div className="w-16 h-3 bg-stone-200 rounded" />
            </div>
          ))}
        </div>
        <div className="h-32 bg-stone-100 rounded" />
      </div>
    </div>
  );
}

// ============================================================================
// DEMO APP
// ============================================================================
export default function AutoProcessingDemo() {
  const [showComparison, setShowComparison] = useState(true);
  const [hasSlides, setHasSlides] = useState(true);
  const [key, setKey] = useState(0);
  
  const handleRestart = () => setKey(k => k + 1);

  return (
    <div className="min-h-screen bg-stone-100 p-6">
      {/* Controls */}
      <div className="max-w-3xl mx-auto mb-6 flex items-center justify-between">
        <h1 className="text-lg font-semibold text-stone-900">
          Компактная форма автообработки
        </h1>
        <div className="flex items-center gap-4">
          <label className="flex items-center gap-2 text-sm text-stone-600">
            <input
              type="checkbox"
              checked={hasSlides}
              onChange={(e) => { setHasSlides(e.target.checked); handleRestart(); }}
              className="rounded"
            />
            Со слайдами
          </label>
          <label className="flex items-center gap-2 text-sm text-stone-600">
            <input
              type="checkbox"
              checked={showComparison}
              onChange={(e) => setShowComparison(e.target.checked)}
              className="rounded"
            />
            Сравнение
          </label>
          <button
            onClick={handleRestart}
            className="px-3 py-1.5 text-sm font-medium text-blue-600 hover:bg-blue-50 rounded-lg"
          >
            Перезапустить
          </button>
        </div>
      </div>
      
      {/* Comparison view */}
      <div className={`max-w-3xl mx-auto ${showComparison ? 'grid grid-cols-2 gap-6' : 'flex justify-center'}`}>
        {showComparison && <OldDesignMock />}
        
        <div>
          {showComparison && (
            <div className="text-center mb-4">
              <div className="text-sm font-medium text-stone-900 mb-1">Новый дизайн</div>
              <div className="text-xs text-stone-500">~280px высота (без слайдов ~250px)</div>
            </div>
          )}
          <AutoProcessingModal
            key={key}
            fileName="2026.01 Форум Табтим. Тестовая тема (Светлана Дмитрук).mp3"
            hasSlides={hasSlides}
            onCancel={() => alert('Отменено')}
            onOpenArchive={() => alert('Открыть в архиве')}
          />
        </div>
      </div>
      
      {/* Summary */}
      <div className="max-w-3xl mx-auto mt-8 p-4 bg-white rounded-xl border border-stone-200">
        <h3 className="text-sm font-medium text-stone-900 mb-3">Изменения:</h3>
        <ul className="space-y-1 text-sm text-stone-600">
          <li>✓ Убран список файлов после завершения</li>
          <li>✓ Убраны метрики этапов (5:01, 4197 симв.)</li>
          <li>✓ Уменьшены отступы между этапами</li>
          <li>✓ Компактные иконки статуса (20px → 16px)</li>
          <li>✓ Кнопка "Открыть в архиве" вместо списка файлов</li>
          <li>✓ Высота ~280px вместо ~500px</li>
        </ul>
      </div>
    </div>
  );
}
