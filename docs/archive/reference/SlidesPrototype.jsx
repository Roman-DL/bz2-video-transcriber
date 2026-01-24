import { useState, useRef, useMemo } from 'react';

// ============================================================================
// ICONS
// ============================================================================
const Icons = {
  Music: ({ className }) => <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M9 18V5l12-2v13"/><circle cx="6" cy="18" r="3"/><circle cx="18" cy="16" r="3"/></svg>,
  Video: ({ className }) => <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="m22 8-6 4 6 4V8Z"/><rect width="14" height="12" x="2" y="6" rx="2"/></svg>,
  Image: ({ className }) => <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect width="18" height="18" x="3" y="3" rx="2"/><circle cx="9" cy="9" r="2"/><path d="m21 15-3.086-3.086a2 2 0 0 0-2.828 0L6 21"/></svg>,
  Paperclip: ({ className }) => <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="m21.44 11.05-9.19 9.19a6 6 0 0 1-8.49-8.49l8.57-8.57A4 4 0 1 1 18 8.84l-8.59 8.57a2 2 0 0 1-2.83-2.83l8.49-8.48"/></svg>,
  Plus: ({ className }) => <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>,
  X: ({ className }) => <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>,
  ChevronDown: ({ className }) => <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="6 9 12 15 18 9"/></svg>,
  ChevronRight: ({ className }) => <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="9 18 15 12 9 6"/></svg>,
  ListOrdered: ({ className }) => <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="10" y1="6" x2="21" y2="6"/><line x1="10" y1="12" x2="21" y2="12"/><line x1="10" y1="18" x2="21" y2="18"/><path d="M4 6h1v4"/><path d="M4 10h2"/><path d="M6 18H4c0-1 2-2 2-3s-1-1.5-2-1"/></svg>,
  Zap: ({ className }) => <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>,
  Clock: ({ className }) => <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>,
  Upload: ({ className }) => <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>,
  Trash2: ({ className }) => <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M3 6h18"/><path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6"/><path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2"/></svg>,
  Settings: ({ className }) => <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z"/><circle cx="12" cy="12" r="3"/></svg>,
  RefreshCw: ({ className }) => <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="23 4 23 10 17 10"/><polyline points="1 20 1 14 7 14"/><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/></svg>,
  Inbox: ({ className }) => <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="22 12 16 12 14 15 10 15 8 12 2 12"/><path d="M5.45 5.11 2 12v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6l-3.45-6.89A2 2 0 0 0 16.76 4H7.24a2 2 0 0 0-1.79 1.11z"/></svg>,
  Archive: ({ className }) => <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect width="20" height="5" x="2" y="3" rx="1"/><path d="M4 8v11a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8"/><path d="M10 12h4"/></svg>,
  Search: ({ className }) => <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>,
  Check: ({ className }) => <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="20 6 9 17 4 12"/></svg>,
  CheckCircle: ({ className }) => <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>,
  Circle: ({ className }) => <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="10"/></svg>,
  Play: ({ className }) => <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polygon points="5 3 19 12 5 21 5 3"/></svg>,
  FileText: ({ className }) => <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/></svg>,
  Sparkles: ({ className }) => <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="m12 3-1.912 5.813a2 2 0 0 1-1.275 1.275L3 12l5.813 1.912a2 2 0 0 1 1.275 1.275L12 21l1.912-5.813a2 2 0 0 1 1.275-1.275L21 12l-5.813-1.912a2 2 0 0 1-1.275-1.275L12 3Z"/></svg>,
  Cloud: ({ className }) => <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M17.5 19H9a7 7 0 1 1 6.71-9h1.79a4.5 4.5 0 1 1 0 9Z"/></svg>,
  ArrowLeft: ({ className }) => <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="19" y1="12" x2="5" y2="12"/><polyline points="12 19 5 12 12 5"/></svg>,
  Layers: ({ className }) => <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polygon points="12 2 2 7 12 12 22 7 12 2"/><polyline points="2 17 12 22 22 17"/><polyline points="2 12 12 17 22 12"/></svg>,
};

// ============================================================================
// UTILITIES
// ============================================================================
function formatFileSize(bytes) {
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(0) + ' KB';
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
}

// ============================================================================
// MOCK DATA
// ============================================================================
const MOCK_SLIDES = [
  { id: 1, name: 'IMG_001.jpg', size: 1.8 * 1024 * 1024, color: '#dbeafe' },
  { id: 2, name: 'IMG_002.jpg', size: 2.1 * 1024 * 1024, color: '#dcfce7' },
  { id: 3, name: 'IMG_003.jpg', size: 1.5 * 1024 * 1024, color: '#fef9c3' },
  { id: 4, name: 'IMG_004.jpg', size: 2.3 * 1024 * 1024, color: '#fee2e2' },
  { id: 5, name: 'IMG_005.jpg', size: 1.9 * 1024 * 1024, color: '#f3e8ff' },
  { id: 6, name: 'IMG_006.jpg', size: 2.0 * 1024 * 1024, color: '#e0f2fe' },
  { id: 7, name: 'IMG_007.jpg', size: 1.7 * 1024 * 1024, color: '#fce7f3' },
  { id: 8, name: 'IMG_008.jpg', size: 2.2 * 1024 * 1024, color: '#d1fae5' },
];

const MOCK_EXTRACTED_TEXT = `## Слайд 1: Введение в продукт

**Формула 1** — сбалансированное питание для контроля веса.

### Состав на порцию (26г):
| Нутриент | Количество | % от РСП |
|----------|------------|----------|
| Белок | 18г | 36% |
| Клетчатка | 3г | 12% |
| Витамин C | 60мг | 100% |

---

## Слайд 2: Преимущества

1. **Удобство** — готовится за 2 минуты
2. **Контроль калорий** — 220 ккал на порцию
3. **Полноценное питание** — 23 витамина и минерала

> "Продукт №1 в категории заменителей питания" — Euromonitor 2025

---

## Слайд 3: Программа снижения веса

**5 шагов к результату:**
- Завтрак: Формула 1 + фрукты
- Перекус: Протеиновый батончик
- Обед: Сбалансированная еда
- Перекус: Формула 1
- Ужин: Лёгкий салат с белком

**Результат:** -3-5 кг за месяц при соблюдении программы

---

## Слайд 4: Статистика эффективности

### Результаты исследования (n=500):
| Показатель | До | После 3 мес. |
|------------|-----|--------------|
| Средний вес | 78 кг | 72 кг |
| ИМТ | 27.2 | 25.1 |
| Объём талии | 92 см | 85 см |

*Данные клинического исследования 2024 г.*`;

const INBOX_FILES = [
  { id: 1, name: '2026.01 Форум Табтим. Тестовая тема (Светлана Дмитрук).mp3', type: 'audio', speaker: 'Светлана Дмитрук', duration: '5:01', slides: [] },
  { id: 2, name: 'SV Закрытие ПО, возражения.mp4', type: 'video', speaker: 'Кухаренко Женя', duration: '12:34', slides: [] },
  { id: 3, name: '2026.01 Школа успеха. Продукт (Иванова Мария).mp3', type: 'audio', speaker: 'Иванова Мария', duration: '45:12', slides: MOCK_SLIDES },
];

// ============================================================================
// SLIDES MODAL
// ============================================================================
function SlidesModal({ isOpen, onClose, slides, onSlidesChange, fileName }) {
  const fileInputRef = useRef(null);
  const [dragOver, setDragOver] = useState(false);
  
  const totalSize = slides.reduce((acc, s) => acc + s.size, 0);
  
  const handleAddFiles = (files) => {
    const newSlides = Array.from(files).map((f, idx) => ({
      id: Date.now() + idx,
      name: f.name,
      size: f.size,
      color: ['#dbeafe', '#dcfce7', '#fef9c3', '#fee2e2', '#f3e8ff'][idx % 5],
    }));
    onSlidesChange([...slides, ...newSlides]);
  };
  
  const handleRemove = (id) => {
    onSlidesChange(slides.filter(s => s.id !== id));
  };
  
  const handleClearAll = () => {
    onSlidesChange([]);
  };
  
  const handleDrop = (e) => {
    e.preventDefault();
    setDragOver(false);
    handleAddFiles(e.dataTransfer.files);
  };
  
  if (!isOpen) return null;
  
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40">
      <div className="w-full max-w-2xl bg-white rounded-2xl shadow-xl overflow-hidden flex flex-col max-h-[80vh]">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-stone-200">
          <div>
            <h2 className="text-lg font-semibold text-stone-900">Слайды презентации</h2>
            <p className="text-sm text-stone-500 truncate max-w-md" title={fileName}>{fileName}</p>
          </div>
          <button onClick={onClose} className="p-2 text-stone-400 hover:text-stone-600 hover:bg-stone-100 rounded-lg">
            <Icons.X className="w-5 h-5" />
          </button>
        </div>
        
        {/* Drop Zone */}
        <div className="px-5 pt-4">
          <div
            onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
            onDragLeave={() => setDragOver(false)}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
            className={`border-2 border-dashed rounded-xl p-6 text-center cursor-pointer transition-all ${
              dragOver ? 'border-blue-500 bg-blue-50' : 'border-stone-300 bg-stone-50 hover:border-blue-400 hover:bg-blue-50/50'
            }`}
          >
            <input
              ref={fileInputRef}
              type="file"
              multiple
              accept="image/*,.pdf"
              onChange={(e) => handleAddFiles(e.target.files)}
              className="hidden"
            />
            <div className="flex flex-col items-center gap-2">
              <div className={`p-3 rounded-full ${dragOver ? 'bg-blue-100' : 'bg-stone-100'}`}>
                <Icons.Upload className={`w-6 h-6 ${dragOver ? 'text-blue-600' : 'text-stone-400'}`} />
              </div>
              <p className="text-sm font-medium text-stone-700">Перетащите файлы сюда</p>
              <p className="text-xs text-stone-500">или <span className="text-blue-600 underline">выберите</span> на компьютере</p>
              <div className="flex items-center gap-2 text-xs text-stone-400 mt-1">
                <Icons.Image className="w-4 h-4" />
                <span>JPG, PNG</span>
                <span className="text-stone-300">•</span>
                <Icons.FileText className="w-4 h-4" />
                <span>PDF</span>
              </div>
            </div>
          </div>
        </div>
        
        {/* Slides Grid */}
        <div className="flex-1 overflow-y-auto px-5 py-4">
          {slides.length > 0 ? (
            <>
              <div className="flex items-center justify-between mb-3">
                <span className="text-sm font-medium text-stone-700">
                  Загружено: {slides.length} файлов ({formatFileSize(totalSize)})
                </span>
                <button onClick={handleClearAll} className="text-xs text-red-500 hover:text-red-600">
                  Удалить все
                </button>
              </div>
              <div className="grid grid-cols-4 gap-3">
                {slides.map((slide, idx) => (
                  <div key={slide.id} className="group relative aspect-[4/3] rounded-lg overflow-hidden border border-stone-200" style={{ backgroundColor: slide.color }}>
                    <div className="absolute inset-0 flex items-center justify-center text-stone-500 text-sm font-medium">
                      {idx + 1}
                    </div>
                    <div className="absolute inset-0 bg-black/0 group-hover:bg-black/40 transition-colors flex items-center justify-center opacity-0 group-hover:opacity-100">
                      <button onClick={() => handleRemove(slide.id)} className="p-1.5 bg-white rounded-lg text-stone-600 hover:text-red-600">
                        <Icons.Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                    <div className="absolute top-1 left-1 px-1.5 py-0.5 bg-black/60 rounded text-xs text-white font-medium">
                      {idx + 1}
                    </div>
                    <div className="absolute bottom-0 left-0 right-0 px-2 py-1 bg-gradient-to-t from-black/60 to-transparent">
                      <p className="text-xs text-white truncate">{slide.name}</p>
                    </div>
                  </div>
                ))}
              </div>
            </>
          ) : (
            <div className="flex flex-col items-center justify-center py-12 text-stone-400">
              <Icons.Image className="w-12 h-12 mb-3 opacity-40" />
              <p className="text-sm">Слайды не загружены</p>
              <p className="text-xs mt-1">Добавьте фото или PDF презентации</p>
            </div>
          )}
        </div>
        
        {/* Footer */}
        <div className="flex items-center justify-between px-5 py-4 bg-stone-50 border-t border-stone-200">
          <p className="text-xs text-stone-500">
            {slides.length > 0 
              ? 'Слайды будут обработаны на отдельном шаге перед генерацией лонгрида'
              : 'Слайды можно не добавлять — шаг будет пропущен'
            }
          </p>
          <button onClick={onClose} className="px-4 py-2 text-sm font-medium text-white bg-blue-500 rounded-lg hover:bg-blue-600">
            Готово
          </button>
        </div>
      </div>
    </div>
  );
}

// ============================================================================
// PROCESS BUTTON
// ============================================================================
function ProcessButton({ defaultMode, onProcess }) {
  const [isOpen, setIsOpen] = useState(false);
  
  const modes = [
    { id: 'step', name: 'Пошагово', icon: Icons.ListOrdered, desc: 'Контроль этапов' },
    { id: 'auto', name: 'Авто', icon: Icons.Zap, desc: 'Без остановок' },
  ];
  
  const current = modes.find(m => m.id === defaultMode) || modes[0];
  const Icon = current.icon;
  
  return (
    <div className="relative">
      <div className="flex">
        <button onClick={() => onProcess(defaultMode)} className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-white bg-blue-500 rounded-l-lg hover:bg-blue-600 transition-colors">
          <Icon className="w-3.5 h-3.5" />
          {current.name}
        </button>
        <button onClick={() => setIsOpen(!isOpen)} className="flex items-center px-1.5 text-white bg-blue-500 border-l border-blue-400 rounded-r-lg hover:bg-blue-600 transition-colors">
          <Icons.ChevronDown className={`w-3.5 h-3.5 transition-transform ${isOpen ? 'rotate-180' : ''}`} />
        </button>
      </div>
      
      {isOpen && (
        <>
          <div className="fixed inset-0 z-10" onClick={() => setIsOpen(false)} />
          <div className="absolute right-0 z-20 mt-1 w-40 bg-white border border-stone-200 rounded-lg shadow-lg overflow-hidden">
            {modes.map((mode) => {
              const MIcon = mode.icon;
              return (
                <button key={mode.id} onClick={() => { onProcess(mode.id); setIsOpen(false); }}
                  className={`w-full flex items-center gap-2 px-3 py-2 text-left hover:bg-stone-50 ${mode.id === defaultMode ? 'bg-blue-50' : ''}`}>
                  <MIcon className="w-4 h-4 text-stone-400" />
                  <div>
                    <div className="text-sm text-stone-700">{mode.name}</div>
                    <div className="text-xs text-stone-400">{mode.desc}</div>
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

// ============================================================================
// INBOX CARD
// ============================================================================
function InboxCard({ file, onProcess, onOpenSlides, onUpdateSlides }) {
  const isVideo = file.type === 'video';
  const FileIcon = isVideo ? Icons.Video : Icons.Music;
  const hasSlides = file.slides && file.slides.length > 0;
  const totalSize = hasSlides ? file.slides.reduce((acc, s) => acc + s.size, 0) : 0;
  
  return (
    <div className="bg-white border border-stone-200 rounded-xl p-3 hover:border-stone-300 transition-colors">
      {/* Header */}
      <div className="flex items-start gap-3">
        <div className={`p-2 rounded-lg flex-shrink-0 ${isVideo ? 'bg-purple-50' : 'bg-blue-50'}`}>
          <FileIcon className={`w-5 h-5 ${isVideo ? 'text-purple-500' : 'text-blue-500'}`} />
        </div>
        <div className="flex-1 min-w-0">
          <h3 className="text-sm font-medium text-stone-900 truncate" title={file.name}>{file.name}</h3>
          <div className="flex items-center gap-2 mt-0.5 text-xs text-stone-500">
            {file.speaker && <span>{file.speaker}</span>}
            {file.speaker && file.duration && <span>•</span>}
            {file.duration && (
              <span className="flex items-center gap-1">
                <Icons.Clock className="w-3 h-3" />
                {file.duration}
              </span>
            )}
          </div>
        </div>
      </div>
      
      {/* Slides section */}
      <div className="mt-3 pt-3 border-t border-stone-100">
        {hasSlides ? (
          <button onClick={() => onOpenSlides(file)} className="flex items-center gap-2 px-2 py-1.5 text-xs rounded-lg bg-emerald-50 text-emerald-700 hover:bg-emerald-100 transition-colors">
            <Icons.Paperclip className="w-3.5 h-3.5" />
            <span className="font-medium">{file.slides.length} слайдов</span>
            <span className="text-emerald-500">({formatFileSize(totalSize)})</span>
            <Icons.ChevronRight className="w-3.5 h-3.5 ml-auto text-emerald-400" />
          </button>
        ) : (
          <button onClick={() => onOpenSlides(file)} className="flex items-center gap-1.5 px-2 py-1.5 text-xs text-stone-500 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-colors">
            <Icons.Plus className="w-3.5 h-3.5" />
            <span>Добавить слайды</span>
          </button>
        )}
      </div>
      
      {/* Action */}
      <div className="mt-3 flex justify-end">
        <ProcessButton defaultMode="step" onProcess={(mode) => onProcess(file, mode)} />
      </div>
    </div>
  );
}

// ============================================================================
// MAIN SCREEN
// ============================================================================
function MainScreen({ files, onProcess, onOpenSlides, onUpdateSlides }) {
  return (
    <div className="flex flex-col h-full bg-stone-50">
      {/* Header */}
      <header className="flex items-center justify-between px-6 py-4 bg-white border-b border-stone-200">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-gradient-to-br from-blue-500 to-blue-600 rounded-lg">
            <Icons.Video className="w-5 h-5 text-white" />
          </div>
          <div>
            <h1 className="text-lg font-semibold text-stone-900">БЗ Транскрибатор</h1>
            <span className="text-xs text-stone-400">v0.50.0 • Прототип слайдов</span>
          </div>
        </div>
        <button className="p-2 text-stone-400 hover:text-stone-600 hover:bg-stone-100 rounded-lg">
          <Icons.Settings className="w-5 h-5" />
        </button>
      </header>
      
      {/* Content */}
      <div className="flex flex-1 overflow-hidden">
        {/* Inbox */}
        <aside className="w-80 flex flex-col bg-white border-r border-stone-200">
          <div className="flex items-center justify-between px-4 py-3 border-b border-stone-100">
            <div className="flex items-center gap-2">
              <Icons.Inbox className="w-5 h-5 text-stone-400" />
              <h2 className="font-medium text-stone-900">Inbox</h2>
              <span className="text-xs font-medium text-stone-400 bg-stone-100 px-2 py-0.5 rounded-full">{files.length}</span>
            </div>
            <button className="p-1.5 text-stone-400 hover:text-stone-600 hover:bg-stone-100 rounded-lg">
              <Icons.RefreshCw className="w-4 h-4" />
            </button>
          </div>
          
          <div className="flex-1 p-4 space-y-3 overflow-y-auto">
            {files.map(file => (
              <InboxCard
                key={file.id}
                file={file}
                onProcess={onProcess}
                onOpenSlides={onOpenSlides}
                onUpdateSlides={onUpdateSlides}
              />
            ))}
          </div>
        </aside>
        
        {/* Archive placeholder */}
        <main className="flex-1 flex items-center justify-center bg-stone-100">
          <div className="text-center text-stone-400">
            <Icons.Archive className="w-16 h-16 mx-auto mb-4 opacity-30" />
            <p className="text-lg font-medium text-stone-500">Архив</p>
            <p className="text-sm mt-1">Обработанные материалы</p>
          </div>
        </main>
      </div>
    </div>
  );
}

// ============================================================================
// STEP BY STEP: SLIDES RESULT VIEW
// ============================================================================
function SlidesResultView({ data }) {
  return (
    <div className="flex flex-col h-full bg-white rounded-xl border border-stone-200 overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-stone-200">
        <div>
          <h3 className="text-sm font-medium text-stone-900">Извлечённые данные со слайдов</h3>
          <div className="flex items-center gap-3 mt-1 text-xs text-stone-500">
            <span>{data.slidesCount} слайдов</span>
            <span>•</span>
            <span>{data.chars.toLocaleString()} симв.</span>
            <span>•</span>
            <span>{data.tables} таблиц</span>
            <span>•</span>
            <span>{data.time}</span>
          </div>
        </div>
        <div className="text-right">
          <div className="flex items-center gap-1.5 text-xs text-stone-500">
            <Icons.Cloud className="w-3.5 h-3.5 text-blue-500" />
            <span>{data.model}</span>
          </div>
        </div>
      </div>
      
      {/* Content */}
      <div className="flex-1 overflow-y-auto p-4">
        <pre className="whitespace-pre-wrap text-sm text-stone-700 font-sans leading-relaxed">
          {data.text}
        </pre>
      </div>
      
      {/* Footer */}
      <div className="flex items-center justify-between px-4 py-2 bg-stone-50 border-t border-stone-200 text-xs text-stone-500">
        <span>Токены: {data.tokens.input.toLocaleString()} вх. / {data.tokens.output.toLocaleString()} вых.</span>
        <span>~${data.cost.toFixed(3)}</span>
      </div>
    </div>
  );
}

// ============================================================================
// STEP BY STEP SCREEN
// ============================================================================
function StepByStepScreen({ file, onBack }) {
  const hasSlides = file.slides && file.slides.length > 0;
  
  const STEPS = useMemo(() => {
    const base = [
      { id: 'parse', label: 'Парсинг метаданных', icon: Icons.FileText },
      { id: 'transcribe', label: 'Транскрипция (Whisper)', icon: Icons.Music },
      { id: 'clean', label: 'Очистка текста', icon: Icons.Sparkles },
    ];
    
    if (hasSlides) {
      base.push({ id: 'slides', label: 'Извлечение слайдов', icon: Icons.Layers });
    }
    
    base.push(
      { id: 'longread', label: 'Генерация лонгрида', icon: Icons.FileText },
      { id: 'summarize', label: 'Генерация конспекта', icon: Icons.FileText },
      { id: 'chunk', label: 'Разбиение на чанки', icon: Icons.Layers },
      { id: 'save', label: 'Сохранение', icon: Icons.Check },
    );
    
    return base;
  }, [hasSlides]);
  
  const [completedSteps, setCompletedSteps] = useState(new Set(['parse', 'transcribe', 'clean', 'slides']));
  const [activeTab, setActiveTab] = useState('slides');
  
  const slidesData = {
    slidesCount: file.slides?.length || 0,
    chars: 1847,
    tables: 2,
    time: '12с',
    model: 'claude-haiku-4.5',
    tokens: { input: 8420, output: 1250 },
    cost: 0.012,
    text: MOCK_EXTRACTED_TEXT,
  };
  
  const getStepStatus = (stepId) => {
    if (completedSteps.has(stepId)) return 'completed';
    const completedArray = Array.from(completedSteps);
    const lastCompleted = STEPS.findIndex(s => s.id === completedArray[completedArray.length - 1]);
    const currentIndex = STEPS.findIndex(s => s.id === stepId);
    if (currentIndex === lastCompleted + 1) return 'next';
    return 'pending';
  };
  
  const tabs = STEPS.filter(s => completedSteps.has(s.id) && s.id !== 'save').map(s => ({
    id: s.id,
    label: s.id === 'slides' ? 'Слайды' : s.label.split(' ')[0],
  }));
  
  return (
    <div className="flex flex-col h-full bg-stone-100">
      {/* Header */}
      <header className="flex items-center justify-between px-6 py-4 bg-white border-b border-stone-200">
        <div className="flex items-center gap-4">
          <button onClick={onBack} className="p-2 text-stone-400 hover:text-stone-600 hover:bg-stone-100 rounded-lg">
            <Icons.ArrowLeft className="w-5 h-5" />
          </button>
          <div>
            <span className="text-xs font-semibold uppercase tracking-wider text-stone-400">Пошаговая обработка</span>
            <h1 className="text-base font-medium text-stone-900 truncate max-w-lg">{file.name}</h1>
          </div>
        </div>
        {hasSlides && (
          <div className="flex items-center gap-2 px-3 py-1.5 bg-emerald-50 text-emerald-700 rounded-lg text-xs">
            <Icons.Paperclip className="w-3.5 h-3.5" />
            <span>{file.slides.length} слайдов прикреплено</span>
          </div>
        )}
      </header>
      
      {/* Content */}
      <div className="flex flex-1 overflow-hidden">
        {/* Left: Steps */}
        <aside className="w-72 flex flex-col bg-white border-r border-stone-200 p-4 overflow-y-auto">
          <h4 className="text-xs font-semibold uppercase tracking-wider text-stone-400 mb-3">Этапы обработки</h4>
          <div className="space-y-1">
            {STEPS.map((step, idx) => {
              const status = getStepStatus(step.id);
              const Icon = step.icon;
              const isSlides = step.id === 'slides';
              
              return (
                <button
                  key={step.id}
                  onClick={() => status === 'completed' && step.id !== 'save' && setActiveTab(step.id)}
                  className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg text-left transition-colors ${
                    activeTab === step.id ? 'bg-blue-50 border border-blue-200' : 
                    status === 'completed' ? 'hover:bg-stone-50' : ''
                  }`}
                >
                  <div className={`w-6 h-6 rounded-full flex items-center justify-center flex-shrink-0 ${
                    status === 'completed' ? 'bg-emerald-100' :
                    status === 'next' ? 'bg-blue-100' : 'bg-stone-100'
                  }`}>
                    {status === 'completed' ? (
                      <Icons.Check className="w-3.5 h-3.5 text-emerald-600" />
                    ) : (
                      <span className={`text-xs font-medium ${status === 'next' ? 'text-blue-600' : 'text-stone-400'}`}>
                        {idx + 1}
                      </span>
                    )}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className={`text-sm font-medium truncate ${
                      status === 'completed' ? 'text-stone-900' :
                      status === 'next' ? 'text-blue-600' : 'text-stone-400'
                    }`}>
                      {step.label}
                    </div>
                    {isSlides && (
                      <div className="text-xs text-emerald-600">{file.slides?.length} файлов</div>
                    )}
                  </div>
                </button>
              );
            })}
          </div>
        </aside>
        
        {/* Right: Result */}
        <main className="flex-1 flex flex-col p-4 overflow-hidden">
          {/* Tabs */}
          <div className="flex gap-1 mb-4 overflow-x-auto">
            {tabs.map(tab => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`px-3 py-1.5 text-sm font-medium rounded-lg whitespace-nowrap transition-colors ${
                  activeTab === tab.id
                    ? 'text-blue-600 bg-blue-50 border border-blue-200'
                    : 'text-stone-500 hover:text-stone-700 hover:bg-stone-100'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>
          
          {/* Result content */}
          <div className="flex-1 min-h-0">
            {activeTab === 'slides' && hasSlides ? (
              <SlidesResultView data={slidesData} />
            ) : (
              <div className="h-full bg-white rounded-xl border border-stone-200 flex items-center justify-center text-stone-400">
                <div className="text-center">
                  <Icons.FileText className="w-12 h-12 mx-auto mb-3 opacity-30" />
                  <p className="text-sm">Результат шага "{activeTab}"</p>
                </div>
              </div>
            )}
          </div>
        </main>
      </div>
    </div>
  );
}

// ============================================================================
// MAIN APP
// ============================================================================
export default function SlidesPrototypeApp() {
  const [screen, setScreen] = useState('main'); // main | stepbystep
  const [files, setFiles] = useState(INBOX_FILES);
  const [selectedFile, setSelectedFile] = useState(null);
  const [modalOpen, setModalOpen] = useState(false);
  const [modalFile, setModalFile] = useState(null);
  
  const handleOpenSlides = (file) => {
    setModalFile(file);
    setModalOpen(true);
  };
  
  const handleUpdateSlides = (fileId, slides) => {
    setFiles(prev => prev.map(f => f.id === fileId ? { ...f, slides } : f));
    if (modalFile?.id === fileId) {
      setModalFile(prev => ({ ...prev, slides }));
    }
  };
  
  const handleProcess = (file, mode) => {
    setSelectedFile(file);
    if (mode === 'step') {
      setScreen('stepbystep');
    } else {
      alert(`Авто-обработка: ${file.name}\nСлайдов: ${file.slides?.length || 0}`);
    }
  };
  
  const handleBack = () => {
    setScreen('main');
    setSelectedFile(null);
  };
  
  return (
    <div className="h-screen flex flex-col">
      {screen === 'main' ? (
        <MainScreen
          files={files}
          onProcess={handleProcess}
          onOpenSlides={handleOpenSlides}
          onUpdateSlides={handleUpdateSlides}
        />
      ) : (
        <StepByStepScreen
          file={selectedFile}
          onBack={handleBack}
        />
      )}
      
      <SlidesModal
        isOpen={modalOpen}
        onClose={() => setModalOpen(false)}
        slides={modalFile?.slides || []}
        onSlidesChange={(slides) => handleUpdateSlides(modalFile?.id, slides)}
        fileName={modalFile?.name || ''}
      />
    </div>
  );
}
