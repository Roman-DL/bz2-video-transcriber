import { useState, useMemo, useRef, useEffect } from 'react';

// ============================================================================
// ICONS (inline SVG)
// ============================================================================
const Icons = {
  CheckCircle: ({ className }) => (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/>
    </svg>
  ),
  Circle: ({ className }) => (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <circle cx="12" cy="12" r="10"/>
    </svg>
  ),
  Play: ({ className }) => (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polygon points="5 3 19 12 5 21 5 3"/>
    </svg>
  ),
  RefreshCw: ({ className }) => (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="23 4 23 10 17 10"/><polyline points="1 20 1 14 7 14"/>
      <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/>
    </svg>
  ),
  FileText: ({ className }) => (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
      <polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/>
    </svg>
  ),
  AudioLines: ({ className }) => (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M2 10v3"/><path d="M6 6v11"/><path d="M10 3v18"/><path d="M14 8v7"/><path d="M18 5v13"/><path d="M22 10v3"/>
    </svg>
  ),
  Sparkles: ({ className }) => (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="m12 3-1.912 5.813a2 2 0 0 1-1.275 1.275L3 12l5.813 1.912a2 2 0 0 1 1.275 1.275L12 21l1.912-5.813a2 2 0 0 1 1.275-1.275L21 12l-5.813-1.912a2 2 0 0 1-1.275-1.275L12 3Z"/>
      <path d="M5 3v4"/><path d="M19 17v4"/><path d="M3 5h4"/><path d="M17 19h4"/>
    </svg>
  ),
  BookOpen: ({ className }) => (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"/><path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"/>
    </svg>
  ),
  ListTree: ({ className }) => (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M21 12h-8"/><path d="M21 6H8"/><path d="M21 18h-8"/><path d="M3 6v4c0 1.1.9 2 2 2h3"/><path d="M3 10v6c0 1.1.9 2 2 2h3"/>
    </svg>
  ),
  Layers: ({ className }) => (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polygon points="12 2 2 7 12 12 22 7 12 2"/><polyline points="2 17 12 22 22 17"/><polyline points="2 12 12 17 22 12"/>
    </svg>
  ),
  Save: ({ className }) => (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/>
      <polyline points="17 21 17 13 7 13 7 21"/><polyline points="7 3 7 8 15 8"/>
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
  Settings: ({ className }) => (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z"/>
      <circle cx="12" cy="12" r="3"/>
    </svg>
  ),
  Clock: ({ className }) => (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>
    </svg>
  ),
  Loader: ({ className }) => (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <line x1="12" y1="2" x2="12" y2="6"/><line x1="12" y1="18" x2="12" y2="22"/>
      <line x1="4.93" y1="4.93" x2="7.76" y2="7.76"/><line x1="16.24" y1="16.24" x2="19.07" y2="19.07"/>
      <line x1="2" y1="12" x2="6" y2="12"/><line x1="18" y1="12" x2="22" y2="12"/>
      <line x1="4.93" y1="19.07" x2="7.76" y2="16.24"/><line x1="16.24" y1="7.76" x2="19.07" y2="4.93"/>
    </svg>
  ),
  ArrowUpDown: ({ className }) => (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <line x1="12" y1="3" x2="12" y2="21"/><polyline points="18 9 12 3 6 9"/><polyline points="6 15 12 21 18 15"/>
    </svg>
  ),
  ArrowLeft: ({ className }) => (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <line x1="19" y1="12" x2="5" y2="12"/><polyline points="12 19 5 12 12 5"/>
    </svg>
  ),
  Activity: ({ className }) => (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>
    </svg>
  ),
  Columns: ({ className }) => (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <rect x="3" y="3" width="18" height="18" rx="2"/><line x1="12" y1="3" x2="12" y2="21"/>
    </svg>
  ),
};

// ============================================================================
// MODEL PRICING (справочник цен per 1M tokens)
// ============================================================================
const MODEL_PRICING = {
  'claude-sonnet-4-5': { input: 3.00, output: 15.00, name: 'Claude Sonnet 4.5' },
  'claude-haiku-4-5': { input: 0.80, output: 4.00, name: 'Claude Haiku 4.5' },
  'claude-opus-4-5': { input: 15.00, output: 75.00, name: 'Claude Opus 4.5' },
  'large-v3-turbo': { input: 0, output: 0, name: 'Whisper large-v3-turbo' },
  'large-v3': { input: 0, output: 0, name: 'Whisper large-v3' },
  'gemma2:9b': { input: 0, output: 0, name: 'Gemma2 9B' },
};

function calculateCost(model, inputTokens, outputTokens) {
  const pricing = MODEL_PRICING[model];
  if (!pricing || (pricing.input === 0 && pricing.output === 0)) return 0;
  return (inputTokens / 1_000_000 * pricing.input) + (outputTokens / 1_000_000 * pricing.output);
}

// ============================================================================
// CONFIGURATION
// ============================================================================
const STEPS = [
  { id: 'parse', label: 'Парсинг метаданных', shortLabel: 'Метаданные', icon: 'FileText', hasSettings: false, resultTab: 'metadata', description: 'Извлечение метаданных из имени файла' },
  { id: 'transcribe', label: 'Транскрипция (Whisper)', shortLabel: 'Транскрипт', icon: 'AudioLines', hasSettings: true, resultTab: 'rawTranscript', description: 'Извлечение аудио и транскрипция через Whisper' },
  { id: 'clean', label: 'Очистка текста', shortLabel: 'Очистка', icon: 'Sparkles', hasSettings: true, resultTab: 'cleanedTranscript', description: 'Очистка текста с использованием глоссария и LLM' },
  { id: 'longread', label: 'Генерация лонгрида', shortLabel: 'Лонгрид', icon: 'BookOpen', hasSettings: true, resultTab: 'longread', description: 'Генерация структурированного текста из транскрипции' },
  { id: 'summarize', label: 'Генерация конспекта', shortLabel: 'Конспект', icon: 'ListTree', hasSettings: true, resultTab: 'summary', description: 'Создание конспекта с ключевыми тезисами' },
  { id: 'chunk', label: 'Разбиение на чанки', shortLabel: 'Чанки', icon: 'Layers', hasSettings: true, resultTab: 'chunks', description: 'Разбиение на семантические чанки по H2 заголовкам' },
  { id: 'save', label: 'Сохранение в архив', shortLabel: 'Сохранение', icon: 'Save', hasSettings: false, description: 'Сохранение всех результатов в архив' },
];

// ============================================================================
// MOCK DATA
// ============================================================================
const MOCK_RESULTS = {
  metadata: {
    date: '2026-01-01',
    event: 'ВЫЕЗД',
    eventFull: 'Форум Табтим',
    topic: 'Тестовая тема',
    speaker: 'Светлана Дмитрук',
    videoId: '2026-01-01_форум-табтим_тестовая-тема',
    contentType: 'Обучающий',
    category: 'Выездное',
    duration: '5:01',
  },
  rawTranscript: {
    text: `Спасибо, Даша, огромное за вступительную часть. Всем ребятам привет, кто первый раз. Добро пожаловать на более серьезную, действительно, школу. И сегодня тема у нас будет полная оценка, но мы не будем разбирать полную оценку. Я вам хочу сказать, что у нас каждый месяц проходит группа роста, вообще-то. И можно всегда подключиться на группу роста и посмотреть теорию, как проводить полную оценку. И кто-то из вас, естественно, полные оценки уже проводит. Кто-то вот есть новенькие ребята, будут проводить. Но я по опыту скажу, что полная оценка, ее боятся больше, чем экспресс-оценку. Побаиваются. Я уже про это знаю. Я уже не помню, что было 10 лет назад, потому что... Меня многие же знают, я 10 лет уже в компании, 10 лет занимаюсь вопросами питания, консультации провожу. И по сути, как я говорю, что нам нужно очень четко и ловко всего две встречи научиться проводить. Вот, это экспресс-оценка и полная оценка. Скажу сразу же, как бы вы ни научились, сколько бы вы школу бы не посетили и группу роста, самое важное провести 100 экспресс-оценок, и будет все хорошо получаться. Также и 100 ПО, и будет все хорошо получаться.`,
    model: 'large-v3-turbo',
    language: 'ru',
    chars: 1247,
    words: 214,
    confidence: 0.94,
    processingTimeSec: 23,
  },
  cleanedTranscript: {
    text: `Спасибо, Даша, огромное за вступительную часть. Всем ребятам привет, кто первый раз. Добро пожаловать на более серьезную школу. Сегодня тема у нас будет полная оценка, но мы не будем разбирать полную оценку. Я вам хочу сказать, что у нас каждый месяц проходит группа роста. Можно всегда подключиться на группу роста и посмотреть теорию, как проводить полную оценку. Кто-то из вас, естественно, полные оценки уже проводит. Кто-то есть новенькие ребята, будут проводить. Но я по опыту скажу, что полную оценку её боятся больше, чем экспресс-оценку. Побаиваются. Я уже про это знаю. Я уже не помню, что было 10 лет назад, потому что меня многие знают, я 10 лет уже в компании, 10 лет занимаюсь вопросами питания, консультации провожу. По сути, как я говорю, нам нужно очень четко и ловко всего две встречи научиться проводить. Это экспресс-оценка и полная оценка. Скажу сразу же, как бы вы ни учились, сколько бы школ и групп роста ни посетили, самое важное провести 100 экспресс-оценок, и будет все хорошо получаться. Также и 100 ПО, и будет все хорошо получаться.`,
    model: 'claude-sonnet-4-5',
    originalChars: 1247,
    chars: 1187,
    words: 198,
    processingTimeSec: 6,
    tokensUsed: { input: 1850, output: 1720 },
  },
  longread: {
    text: `Сегодня поговорим о полной оценке — но не о теории её проведения, а о том, как закрывать сделку. Теорию можно посмотреть на группе роста, которая проходит каждый месяц. Здесь мы разберём практику: как работать с возражениями, что делать с возвратами, как довести клиента до результата.

Это более серьёзная школа для тех, кто уже проводит полные оценки или только начинает.

Привет всем, кто здесь впервые! Добро пожаловать на более серьезную школу. Сегодня мы будем говорить о полной оценке, но не о теории её проведения — теорию можно всегда посмотреть на группе роста, которая проходит каждый месяц. Кто-то из вас уже проводит полные оценки, кто-то только начинает.

По опыту скажу: полную оценку боятся больше, чем экспресс-оценку. Я это знаю и понимаю. Меня многие знают — я 10 лет уже в компании, 10 лет занимаюсь вопросами питания и провожу консультации. По сути, нам нужно научиться очень четко и ловко проводить всего две встречи: экспресс-оценку и полную оценку.

Скажу сразу: как бы вы ни учились, сколько бы школ и групп роста ни посетили, самое важное — провести 100 экспресс-оценок, и всё будет хорошо получаться. То же самое с полными оценками: 100 встреч — и всё пойдёт.`,
    model: 'claude-sonnet-4-5',
    chars: 1156,
    words: 187,
    processingTimeSec: 8,
    tokensUsed: { input: 1720, output: 890 },
  },
  summary: {
    text: `## Суть темы

Тема посвящена работе с возражениями и закрытию продажи на полной оценке. Спикер фокусируется не на теоретической части проведения полной оценки, а на практических моментах.

## Ключевые концепции

• Полную оценку боятся больше, чем экспресс-оценку, потому что здесь нужно продавать и получать возражения
• Для мастерства нужна практика: 100 экспресс-оценок и 100 полных оценок
• Личная уверенность консультанта — ключ к успешному проведению встреч
• Возвраты случаются у всех, даже у опытных консультантов

## Цитаты

«Нам нужно научиться очень четко и ловко проводить всего две встречи: экспресс-оценку и полную оценку»

«Самое важное — провести 100 экспресс-оценок, и всё будет хорошо получаться»`,
    model: 'claude-sonnet-4-5',
    chars: 723,
    words: 98,
    processingTimeSec: 5,
    tokensUsed: { input: 1720, output: 520 },
  },
  chunks: {
    chunks: [
      {
        id: 1,
        title: 'Закрытие полной оценки: работа с возражениями и возвратами',
        text: `Привет всем, кто здесь впервые! Добро пожаловать на более серьезную школу. Сегодня мы будем говорить о полной оценке, но не о теории её проведения — теорию можно всегда посмотреть на группе роста, которая проходит каждый месяц. Кто-то из вас уже проводит полные оценки, кто-то только начинает.

По опыту скажу: полную оценку боятся больше, чем экспресс-оценку. Я это знаю и понимаю. Меня многие знают — я 10 лет уже в компании, 10 лет занимаюсь вопросами питания и провожу консультации.`,
        tokens: 680,
      },
    ],
    totalChunks: 1,
    totalTokens: 680,
    processingTimeSec: 0.2,
  },
  save: {
    files: [
      { name: 'pipeline_results.json', size: '12.4 KB' },
      { name: 'transcript_chunks.json', size: '8.2 KB' },
      { name: 'longread.md', size: '4.1 KB' },
      { name: 'summary.md', size: '2.8 KB' },
      { name: 'transcript_raw.txt', size: '4.4 KB' },
      { name: 'transcript_cleaned.txt', size: '4.2 KB' },
      { name: 'audio.mp3', size: '12.4 MB' },
    ],
    processingTimeSec: 1.2,
  },
};

// ============================================================================
// UTILITIES
// ============================================================================
function formatTime(seconds) {
  if (seconds < 1) return `${Math.round(seconds * 1000)}мс`;
  if (seconds < 60) return `${Math.round(seconds)}с`;
  const mins = Math.floor(seconds / 60);
  const secs = Math.round(seconds % 60);
  return `${mins}м ${secs}с`;
}

function formatCost(cost) {
  if (cost === 0) return 'бесплатно';
  if (cost < 0.01) return `~$${cost.toFixed(4)}`;
  return `~$${cost.toFixed(2)}`;
}

function countWords(text) {
  return text.trim().split(/\s+/).filter(w => w.length > 0).length;
}

function calculateTotals(results) {
  const steps = [
    { data: results.rawTranscript, model: results.rawTranscript.model },
    { data: results.cleanedTranscript, model: results.cleanedTranscript.model },
    { data: results.longread, model: results.longread.model },
    { data: results.summary, model: results.summary.model },
  ];
  
  let totalTime = 0;
  let totalInputTokens = 0;
  let totalOutputTokens = 0;
  let totalCost = 0;
  
  steps.forEach(step => {
    totalTime += step.data.processingTimeSec || 0;
    if (step.data.tokensUsed) {
      totalInputTokens += step.data.tokensUsed.input;
      totalOutputTokens += step.data.tokensUsed.output;
      totalCost += calculateCost(step.model, step.data.tokensUsed.input, step.data.tokensUsed.output);
    }
  });
  
  totalTime += results.chunks.processingTimeSec || 0;
  totalTime += results.save.processingTimeSec || 0;
  
  return { totalTime, totalInputTokens, totalOutputTokens, totalCost };
}

// ============================================================================
// INLINE DIFF VIEW (toggle режим в той же области)
// ============================================================================
function InlineDiffView({ leftText, rightText, leftTitle, rightTitle, onClose }) {
  const leftRef = useRef(null);
  const rightRef = useRef(null);
  const [syncScroll, setSyncScroll] = useState(true);

  const handleScroll = (source) => {
    if (!syncScroll) return;
    const sourceEl = source === 'left' ? leftRef.current : rightRef.current;
    const targetEl = source === 'left' ? rightRef.current : leftRef.current;
    if (sourceEl && targetEl) {
      const scrollPercent = sourceEl.scrollTop / (sourceEl.scrollHeight - sourceEl.clientHeight || 1);
      targetEl.scrollTop = scrollPercent * (targetEl.scrollHeight - targetEl.clientHeight);
    }
  };

  const charDiff = rightText.length - leftText.length;
  const charDiffPercent = Math.round((charDiff / leftText.length) * 100);

  return (
    <div className="flex flex-col h-full bg-white border border-stone-200 rounded-xl overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-5 py-3 bg-stone-50 border-b border-stone-100 flex-shrink-0">
        <div className="flex items-center gap-3">
          <button 
            onClick={onClose}
            className="flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium text-stone-600 bg-white border border-stone-200 rounded-lg hover:bg-stone-50 transition-colors"
          >
            <Icons.ArrowLeft className="w-4 h-4" />
            Назад
          </button>
          <h3 className="text-base font-semibold text-stone-900">Сравнение текстов</h3>
        </div>
        <div className="flex items-center gap-4">
          <label className="flex items-center gap-2 text-sm text-stone-600 cursor-pointer">
            <input 
              type="checkbox" 
              checked={syncScroll}
              onChange={(e) => setSyncScroll(e.target.checked)}
              className="w-4 h-4 rounded border-stone-300 text-blue-600 focus:ring-blue-500"
            />
            <Icons.ArrowUpDown className="w-4 h-4" />
            Синхронный скролл
          </label>
          <span className="text-xs text-stone-500">
            Разница: <strong className={charDiff < 0 ? 'text-emerald-600' : 'text-amber-600'}>
              {charDiff > 0 ? '+' : ''}{charDiff.toLocaleString()} симв.
            </strong>
            {' '}({charDiffPercent > 0 ? '+' : ''}{charDiffPercent}%)
          </span>
        </div>
      </div>
      
      {/* Content - два столбца на всю высоту */}
      <div className="flex-1 flex min-h-0">
        {/* Left panel */}
        <div className="flex-1 flex flex-col border-r border-stone-200 min-h-0">
          <div className="px-4 py-2 bg-stone-100 border-b border-stone-200 flex-shrink-0">
            <span className="text-sm font-medium text-stone-700">{leftTitle}</span>
            <span className="ml-2 text-xs text-stone-500">
              {leftText.length.toLocaleString()} симв. · {countWords(leftText)} слов
            </span>
          </div>
          <div 
            ref={leftRef}
            onScroll={() => handleScroll('left')}
            className="flex-1 p-4 overflow-y-auto min-h-0"
          >
            <p className="text-sm text-stone-700 leading-relaxed whitespace-pre-wrap">
              {leftText}
            </p>
          </div>
        </div>
        
        {/* Right panel */}
        <div className="flex-1 flex flex-col min-h-0">
          <div className="px-4 py-2 bg-emerald-50 border-b border-emerald-100 flex-shrink-0">
            <span className="text-sm font-medium text-emerald-700">{rightTitle}</span>
            <span className="ml-2 text-xs text-emerald-600">
              {rightText.length.toLocaleString()} симв. · {countWords(rightText)} слов
            </span>
          </div>
          <div 
            ref={rightRef}
            onScroll={() => handleScroll('right')}
            className="flex-1 p-4 overflow-y-auto min-h-0"
          >
            <p className="text-sm text-stone-700 leading-relaxed whitespace-pre-wrap">
              {rightText}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

// ============================================================================
// RESULT CONTENT COMPONENTS
// ============================================================================

function MetadataResultContent({ data }) {
  const fields = [
    { label: 'Дата', value: data.date },
    { label: 'Мероприятие', value: data.event },
    { label: 'Тема', value: data.topic },
    { label: 'Спикер', value: data.speaker },
    { label: 'Video ID', value: data.videoId, mono: true },
    { label: 'Тип контента', value: data.contentType },
    { label: 'Категория', value: data.category },
  ];

  return (
    <div className="flex flex-col h-full bg-white border border-stone-200 rounded-xl overflow-hidden">
      <div className="flex items-center justify-between px-5 py-4 bg-stone-50 border-b border-stone-100 flex-shrink-0">
        <h3 className="text-base font-semibold text-stone-900">Метаданные</h3>
        <span className="text-xs text-stone-500 flex items-center gap-1">
          <Icons.Clock className="w-3.5 h-3.5" />
          {data.duration}
        </span>
      </div>
      <div className="flex-1 p-5 overflow-y-auto">
        <div className="grid grid-cols-2 gap-x-6 gap-y-4">
          {fields.map((field, i) => (
            <div key={i} className="flex flex-col gap-1">
              <span className="text-xs font-medium text-stone-400 uppercase tracking-wide">{field.label}</span>
              <span className={`text-sm text-stone-900 ${field.mono ? 'font-mono text-xs bg-stone-100 px-2 py-1 rounded' : 'font-medium'}`}>
                {field.value}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function TranscriptResultContent({ data }) {
  return (
    <div className="flex flex-col h-full bg-white border border-stone-200 rounded-xl overflow-hidden">
      <div className="flex items-center justify-between px-5 py-4 bg-stone-50 border-b border-stone-100 flex-shrink-0">
        <div className="flex items-center gap-3">
          <h3 className="text-base font-semibold text-stone-900">Сырая транскрипция</h3>
          <span className="px-2 py-0.5 bg-stone-200 text-stone-600 text-xs font-mono rounded">{data.model}</span>
        </div>
        <div className="flex items-center gap-4 text-xs text-stone-500">
          <span>{data.language.toUpperCase()}</span>
          <span className="text-stone-300">|</span>
          <span>{data.chars.toLocaleString()} симв.</span>
          <span className="text-stone-300">|</span>
          <span>{data.words} слов</span>
          <span className="text-stone-300">|</span>
          <span className="flex items-center gap-1" title="Confidence (уверенность распознавания)">
            <Icons.Activity className="w-3.5 h-3.5" />
            {Math.round(data.confidence * 100)}%
          </span>
          <span className="text-stone-300">|</span>
          <span className="text-emerald-600">{formatTime(data.processingTimeSec)}</span>
        </div>
      </div>
      <div className="flex-1 p-5 overflow-y-auto min-h-0">
        <p className="text-sm text-stone-700 leading-relaxed whitespace-pre-wrap">
          {data.text}
        </p>
      </div>
    </div>
  );
}

function CleanedTranscriptResultContent({ data, rawData, showDiff, onToggleDiff }) {
  const changePercent = Math.round((1 - data.chars / rawData.chars) * 100);
  const cost = calculateCost(data.model, data.tokensUsed.input, data.tokensUsed.output);
  
  if (showDiff) {
    return (
      <InlineDiffView
        leftText={rawData.text}
        rightText={data.text}
        leftTitle="Транскрипт"
        rightTitle="Очистка"
        onClose={onToggleDiff}
      />
    );
  }
  
  return (
    <div className="flex flex-col h-full bg-white border border-stone-200 rounded-xl overflow-hidden">
      <div className="flex items-center justify-between px-5 py-4 bg-stone-50 border-b border-stone-100 flex-shrink-0">
        <div className="flex items-center gap-3">
          <h3 className="text-base font-semibold text-stone-900">Очищенная транскрипция</h3>
          <span className="px-2 py-0.5 bg-violet-100 text-violet-700 text-xs font-mono rounded">{data.model}</span>
        </div>
        <div className="flex items-center gap-4 text-xs text-stone-500">
          <span>{data.chars.toLocaleString()} симв.</span>
          <span className="text-stone-300">|</span>
          <span>{data.words} слов</span>
          <span className="text-stone-300">|</span>
          <span className="text-emerald-600">-{changePercent}%</span>
          <span className="text-stone-300">|</span>
          <span className="text-emerald-600">{formatTime(data.processingTimeSec)}</span>
        </div>
      </div>
      
      <div className="px-5 py-3 bg-blue-50 border-b border-blue-100 flex-shrink-0">
        <button 
          onClick={onToggleDiff}
          className="flex items-center gap-2 px-3 py-2 text-sm font-medium text-blue-700 bg-white border border-blue-200 rounded-lg hover:bg-blue-50 transition-colors"
        >
          <Icons.Columns className="w-4 h-4" />
          Сравнить с транскриптом
        </button>
      </div>
      
      <div className="flex-1 p-5 overflow-y-auto min-h-0">
        <p className="text-sm text-stone-700 leading-relaxed whitespace-pre-wrap">
          {data.text}
        </p>
      </div>
      
      <div className="px-5 py-3 bg-stone-50 border-t border-stone-100 text-xs text-stone-500 flex items-center justify-between flex-shrink-0">
        <span>Токены: <strong>{data.tokensUsed.input.toLocaleString()}</strong> вх. / <strong>{data.tokensUsed.output.toLocaleString()}</strong> вых.</span>
        <span className="text-violet-600">{formatCost(cost)}</span>
      </div>
    </div>
  );
}

function LongreadResultContent({ data, cleanedData, showDiff, onToggleDiff }) {
  const changePercent = Math.round((data.chars / cleanedData.chars - 1) * 100);
  const cost = calculateCost(data.model, data.tokensUsed.input, data.tokensUsed.output);
  
  if (showDiff) {
    return (
      <InlineDiffView
        leftText={cleanedData.text}
        rightText={data.text}
        leftTitle="Очистка"
        rightTitle="Лонгрид"
        onClose={onToggleDiff}
      />
    );
  }
  
  return (
    <div className="flex flex-col h-full bg-white border border-stone-200 rounded-xl overflow-hidden">
      <div className="flex items-center justify-between px-5 py-4 bg-stone-50 border-b border-stone-100 flex-shrink-0">
        <div className="flex items-center gap-3">
          <h3 className="text-base font-semibold text-stone-900">Лонгрид</h3>
          <span className="px-2 py-0.5 bg-violet-100 text-violet-700 text-xs font-mono rounded">{data.model}</span>
        </div>
        <div className="flex items-center gap-4 text-xs text-stone-500">
          <span>{data.chars.toLocaleString()} симв.</span>
          <span className="text-stone-300">|</span>
          <span>{data.words} слов</span>
          <span className="text-stone-300">|</span>
          <span className={changePercent < 0 ? 'text-emerald-600' : 'text-amber-600'}>
            {changePercent > 0 ? '+' : ''}{changePercent}%
          </span>
          <span className="text-stone-300">|</span>
          <span className="text-emerald-600">{formatTime(data.processingTimeSec)}</span>
        </div>
      </div>
      
      <div className="px-5 py-3 bg-blue-50 border-b border-blue-100 flex-shrink-0">
        <button 
          onClick={onToggleDiff}
          className="flex items-center gap-2 px-3 py-2 text-sm font-medium text-blue-700 bg-white border border-blue-200 rounded-lg hover:bg-blue-50 transition-colors"
        >
          <Icons.Columns className="w-4 h-4" />
          Сравнить с очисткой
        </button>
      </div>
      
      <div className="flex-1 p-5 overflow-y-auto min-h-0">
        <p className="text-sm text-stone-700 leading-relaxed whitespace-pre-wrap">
          {data.text}
        </p>
      </div>
      
      <div className="px-5 py-3 bg-stone-50 border-t border-stone-100 text-xs text-stone-500 flex items-center justify-between flex-shrink-0">
        <span>Токены: <strong>{data.tokensUsed.input.toLocaleString()}</strong> вх. / <strong>{data.tokensUsed.output.toLocaleString()}</strong> вых.</span>
        <span className="text-violet-600">{formatCost(cost)}</span>
      </div>
    </div>
  );
}

function SummaryResultContent({ data }) {
  const cost = calculateCost(data.model, data.tokensUsed.input, data.tokensUsed.output);
  
  return (
    <div className="flex flex-col h-full bg-white border border-stone-200 rounded-xl overflow-hidden">
      <div className="flex items-center justify-between px-5 py-4 bg-stone-50 border-b border-stone-100 flex-shrink-0">
        <div className="flex items-center gap-3">
          <h3 className="text-base font-semibold text-stone-900">Конспект</h3>
          <span className="px-2 py-0.5 bg-violet-100 text-violet-700 text-xs font-mono rounded">{data.model}</span>
        </div>
        <div className="flex items-center gap-4 text-xs text-stone-500">
          <span>{data.chars.toLocaleString()} симв.</span>
          <span className="text-stone-300">|</span>
          <span>{data.words} слов</span>
          <span className="text-stone-300">|</span>
          <span className="text-emerald-600">{formatTime(data.processingTimeSec)}</span>
        </div>
      </div>
      
      <div className="flex-1 p-5 overflow-y-auto min-h-0">
        <div className="text-sm text-stone-700 leading-relaxed whitespace-pre-wrap">
          {data.text}
        </div>
      </div>
      
      <div className="px-5 py-3 bg-stone-50 border-t border-stone-100 text-xs text-stone-500 flex items-center justify-between flex-shrink-0">
        <span>Токены: <strong>{data.tokensUsed.input.toLocaleString()}</strong> вх. / <strong>{data.tokensUsed.output.toLocaleString()}</strong> вых.</span>
        <span className="text-violet-600">{formatCost(cost)}</span>
      </div>
    </div>
  );
}

function ChunksResultContent({ data }) {
  const [expandedChunk, setExpandedChunk] = useState(0);
  
  return (
    <div className="flex flex-col h-full bg-white border border-stone-200 rounded-xl overflow-hidden">
      <div className="flex items-center justify-between px-5 py-4 bg-stone-50 border-b border-stone-100 flex-shrink-0">
        <h3 className="text-base font-semibold text-stone-900">Чанки</h3>
        <div className="flex items-center gap-4 text-xs text-stone-500">
          <span>{data.totalChunks} чанков</span>
          <span className="text-stone-300">|</span>
          <span>{data.totalTokens.toLocaleString()} токенов</span>
        </div>
      </div>
      
      <div className="flex-1 p-5 space-y-3 overflow-y-auto min-h-0">
        {data.chunks.map((chunk, i) => (
          <div 
            key={chunk.id} 
            className={`rounded-xl border-2 transition-all cursor-pointer ${
              expandedChunk === i ? 'border-blue-500 bg-blue-50/30' : 'border-stone-200 hover:border-stone-300'
            }`}
            onClick={() => setExpandedChunk(expandedChunk === i ? -1 : i)}
          >
            <div className="flex items-center justify-between px-4 py-3">
              <div className="flex items-center gap-3">
                <span className="w-7 h-7 flex items-center justify-center bg-blue-500 text-white rounded-lg text-xs font-bold">
                  #{chunk.id}
                </span>
                <span className="font-medium text-stone-900">{chunk.title}</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-xs text-stone-500">{chunk.tokens} токенов</span>
                <Icons.ChevronDown className={`w-4 h-4 text-stone-400 transition-transform ${expandedChunk === i ? 'rotate-180' : ''}`} />
              </div>
            </div>
            
            {expandedChunk === i && (
              <div className="px-4 pb-4">
                <p className="text-sm text-stone-700 leading-relaxed whitespace-pre-wrap bg-white rounded-lg p-4 border border-stone-100">
                  {chunk.text}
                </p>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

// ============================================================================
// SETTINGS PANEL (2 промпта: system и user)
// ============================================================================
function SettingsPanel({ step, onRerun }) {
  const [model, setModel] = useState('claude-sonnet-4-5');
  const [prompts, setPrompts] = useState({
    system: 'system (по умолч.)',
    user: 'user (по умолч.)',
  });
  
  const models = {
    transcribe: [
      { id: 'large-v3-turbo', label: 'large-v3-turbo', type: 'local' },
      { id: 'large-v3', label: 'large-v3', type: 'local' },
    ],
    clean: [
      { id: 'claude-sonnet-4-5', label: 'Claude Sonnet 4.5', type: 'cloud' },
      { id: 'claude-haiku-4-5', label: 'Claude Haiku 4.5', type: 'cloud' },
      { id: 'gemma2:9b', label: 'gemma2:9b', type: 'local' },
    ],
    longread: [
      { id: 'claude-sonnet-4-5', label: 'Claude Sonnet 4.5', type: 'cloud' },
      { id: 'claude-haiku-4-5', label: 'Claude Haiku 4.5', type: 'cloud' },
    ],
    summarize: [
      { id: 'claude-sonnet-4-5', label: 'Claude Sonnet 4.5', type: 'cloud' },
      { id: 'claude-haiku-4-5', label: 'Claude Haiku 4.5', type: 'cloud' },
    ],
    chunk: [
      { id: 'claude-sonnet-4-5', label: 'Claude Sonnet 4.5', type: 'cloud' },
      { id: 'claude-haiku-4-5', label: 'Claude Haiku 4.5', type: 'cloud' },
    ],
  };
  
  const availableModels = models[step] || [];
  const currentModel = availableModels.find(m => m.id === model) || availableModels[0];
  const isLLMStep = ['clean', 'longread', 'summarize', 'chunk'].includes(step);
  
  return (
    <div className="ml-8 mt-2 mb-2 p-4 bg-gradient-to-br from-stone-50 to-stone-100 rounded-xl border border-stone-200">
      {/* Модель */}
      <div className="mb-4">
        <div className="flex items-center gap-2 mb-2">
          <label className="text-xs font-semibold uppercase tracking-wider text-stone-400">Модель</label>
          {currentModel && (
            <span className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${
              currentModel.type === 'cloud' ? 'bg-violet-100 text-violet-700' : 'bg-emerald-100 text-emerald-700'
            }`}>
              {currentModel.type}
            </span>
          )}
        </div>
        <select 
          className="w-full px-3 py-2.5 text-sm bg-white border border-stone-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-100 focus:border-blue-500"
          value={model}
          onChange={(e) => setModel(e.target.value)}
        >
          {availableModels.map(m => (
            <option key={m.id} value={m.id}>{m.label}</option>
          ))}
        </select>
      </div>
      
      {/* Промпты: system и user */}
      {isLLMStep && (
        <div className="mb-4">
          <label className="text-xs font-semibold uppercase tracking-wider text-stone-400 mb-2 block">Промпты</label>
          <div className="grid grid-cols-2 gap-3">
            {['system', 'user'].map(promptType => (
              <div key={promptType}>
                <label className="text-[10px] text-stone-400 uppercase mb-1 block">{promptType}</label>
                <select 
                  className="w-full px-2 py-1.5 text-xs bg-white border border-stone-200 rounded focus:outline-none focus:ring-2 focus:ring-blue-100 focus:border-blue-500"
                  value={prompts[promptType]}
                  onChange={(e) => setPrompts({...prompts, [promptType]: e.target.value})}
                >
                  <option>{promptType} (по умолч.)</option>
                  <option>{promptType}_v2</option>
                  <option>{promptType}_strict</option>
                </select>
              </div>
            ))}
          </div>
        </div>
      )}
      
      <button 
        className="flex items-center justify-center gap-2 w-full px-4 py-2.5 text-sm font-medium text-orange-700 bg-orange-50 border border-orange-200 rounded-lg hover:bg-orange-100 transition-colors"
        onClick={onRerun}
      >
        <Icons.RefreshCw className="w-4 h-4" />
        Перезапустить
      </button>
    </div>
  );
}

// ============================================================================
// OTHER COMPONENTS
// ============================================================================
function ProgressIndicator({ step, progress, elapsed, eta, status }) {
  const stepConfig = STEPS.find(s => s.id === step);
  const Icon = Icons[stepConfig?.icon || 'FileText'];
  
  return (
    <div className="p-5 bg-gradient-to-br from-blue-50 via-blue-50 to-indigo-50 border border-blue-200 rounded-xl relative overflow-hidden">
      <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-blue-500 via-indigo-500 to-blue-500 animate-pulse" />
      <div className="flex items-center gap-2 mb-3">
        <span className="px-2 py-1 bg-blue-500 text-white text-xs font-bold uppercase tracking-wider rounded">Выполняется</span>
        <span className="text-xs text-blue-700 font-medium">Шаг {STEPS.findIndex(s => s.id === step) + 1}</span>
      </div>
      <div className="flex items-center gap-3 mb-3">
        <div className="w-10 h-10 flex items-center justify-center bg-white rounded-xl border border-blue-200">
          <Icon className="w-5 h-5 text-blue-600" />
        </div>
        <div className="flex-1">
          <h3 className="text-base font-semibold text-stone-900">{stepConfig?.label}</h3>
          <p className="text-xs text-stone-500">{status}</p>
        </div>
      </div>
      <div className="mb-2">
        <div className="h-2 bg-white rounded-full overflow-hidden border border-blue-100">
          <div className="h-full bg-gradient-to-r from-blue-500 to-indigo-500 rounded-full transition-all duration-300" style={{ width: `${progress}%` }} />
        </div>
      </div>
      <div className="flex items-center justify-between text-xs">
        <span className="font-mono text-blue-700">{progress}%</span>
        <div className="flex items-center gap-3 text-stone-500">
          <span>{elapsed}</span>
          {eta && <span className="text-blue-600">~{eta}</span>}
        </div>
      </div>
      <button className="flex items-center justify-center gap-2 w-full mt-4 px-4 py-2.5 text-sm font-medium text-stone-600 bg-white border border-stone-200 rounded-lg">
        <Icons.Loader className="w-4 h-4 animate-spin" />
        Выполняется...
      </button>
    </div>
  );
}

function NextStepCard({ step, stepIndex, onExecute }) {
  const stepConfig = STEPS.find(s => s.id === step);
  const Icon = Icons[stepConfig?.icon || 'FileText'];
  
  return (
    <div className="p-5 bg-gradient-to-br from-blue-50 to-indigo-50 border border-blue-200 rounded-xl relative overflow-hidden">
      <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-blue-500 to-indigo-500" />
      <div className="flex items-center gap-2 mb-3">
        <span className="px-2 py-1 bg-white text-blue-600 text-xs font-bold uppercase tracking-wider rounded border border-blue-200">Следующий</span>
        <span className="text-xs text-blue-700 font-medium">Шаг {stepIndex + 1}</span>
      </div>
      <div className="flex items-center gap-3 mb-3">
        <div className="w-10 h-10 flex items-center justify-center bg-white rounded-xl border border-blue-200">
          <Icon className="w-5 h-5 text-blue-600" />
        </div>
        <div className="flex-1">
          <h3 className="text-base font-semibold text-stone-900">{stepConfig?.label}</h3>
          <p className="text-xs text-stone-500">{stepConfig?.description}</p>
        </div>
      </div>
      <button className="flex items-center justify-center gap-2 w-full px-5 py-3 text-sm font-semibold text-white bg-gradient-to-r from-blue-600 to-indigo-600 rounded-lg hover:from-blue-700 hover:to-indigo-700 transition-all shadow-md hover:shadow-lg" onClick={onExecute}>
        <Icons.Play className="w-4 h-4" />
        Выполнить
      </button>
    </div>
  );
}

function CompletionCard({ files, totals, onClose }) {
  return (
    <div className="p-5 bg-gradient-to-br from-emerald-50 to-teal-50 border border-emerald-200 rounded-xl">
      <div className="flex items-center gap-3 mb-4">
        <div className="w-10 h-10 flex items-center justify-center bg-emerald-500 rounded-xl">
          <Icons.CheckCircle className="w-5 h-5 text-white" />
        </div>
        <div>
          <h3 className="text-base font-semibold text-stone-900">Успешно сохранено</h3>
          <p className="text-xs text-stone-500">{files.length} файлов</p>
        </div>
      </div>
      <div className="space-y-1.5 mb-4">
        {files.map((file, i) => (
          <div key={i} className="flex items-center justify-between px-3 py-2 bg-white rounded-lg border border-emerald-100 text-xs">
            <span className="font-mono text-stone-700">{file.name}</span>
            <span className="text-stone-400">{file.size}</span>
          </div>
        ))}
      </div>
      <div className="p-3 bg-white rounded-lg border border-emerald-100 mb-4 space-y-2">
        <div className="flex justify-between text-xs">
          <span className="text-stone-500">Общее время:</span>
          <strong className="text-stone-700">{formatTime(totals.totalTime)}</strong>
        </div>
        <div className="flex justify-between text-xs">
          <span className="text-stone-500">Токены (вх./вых.):</span>
          <strong className="text-stone-700">{totals.totalInputTokens.toLocaleString()} / {totals.totalOutputTokens.toLocaleString()}</strong>
        </div>
        <div className="flex justify-between text-xs">
          <span className="text-stone-500">Стоимость:</span>
          <strong className="text-violet-600">{formatCost(totals.totalCost)}</strong>
        </div>
      </div>
      <button className="flex items-center justify-center gap-2 w-full px-5 py-3 text-sm font-semibold text-white bg-emerald-600 rounded-lg hover:bg-emerald-700 transition-colors" onClick={onClose}>
        Закрыть
      </button>
    </div>
  );
}

function TimelineStep({ step, index, status, isExpanded, onToggleSettings, onSelect, totalSteps }) {
  const stepConfig = STEPS.find(s => s.id === step.id);
  const Icon = Icons[stepConfig?.icon || 'FileText'];
  const statusStyles = {
    completed: { icon: 'text-emerald-500', line: 'bg-emerald-500', text: 'text-stone-900', bg: 'hover:bg-stone-50' },
    current: { icon: 'text-emerald-500', line: 'bg-emerald-500', text: 'text-stone-900', bg: 'hover:bg-stone-50' },
    next: { icon: 'text-blue-500', line: 'bg-stone-200', text: 'text-stone-900', bg: '' },
    pending: { icon: 'text-stone-300', line: 'bg-stone-200', text: 'text-stone-400', bg: '' },
  };
  const styles = statusStyles[status];
  
  return (
    <div className="relative">
      <div className={`flex items-start gap-3 px-3 py-2.5 rounded-lg cursor-pointer transition-colors ${styles.bg}`} onClick={() => { if (status === 'completed' || status === 'current') onSelect(); }}>
        <div className="relative flex flex-col items-center pt-0.5">
          {status === 'completed' || status === 'current' ? (
            <Icons.CheckCircle className={`w-5 h-5 ${styles.icon} flex-shrink-0`} />
          ) : status === 'next' ? (
            <div className="w-5 h-5 rounded-full bg-blue-500 flex items-center justify-center flex-shrink-0">
              <Icons.ChevronRight className="w-3 h-3 text-white" />
            </div>
          ) : (
            <Icons.Circle className={`w-5 h-5 ${styles.icon} flex-shrink-0`} />
          )}
          {index < totalSteps - 1 && <div className={`absolute top-6 left-1/2 -translate-x-1/2 w-0.5 h-8 ${styles.line}`} />}
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <Icon className={`w-4 h-4 ${styles.icon}`} />
            <span className={`text-sm font-medium ${styles.text}`}>{stepConfig?.label}</span>
            {status === 'current' && <span className="px-1.5 py-0.5 bg-emerald-100 text-emerald-700 text-[10px] font-bold uppercase tracking-wide rounded">текущий</span>}
          </div>
          {status === 'current' && stepConfig?.hasSettings && (
            <button className="flex items-center gap-1 mt-1.5 px-2 py-1 text-xs font-medium text-stone-500 bg-stone-100 rounded hover:bg-stone-200 transition-colors" onClick={(e) => { e.stopPropagation(); onToggleSettings(); }}>
              <Icons.Settings className="w-3 h-3" />
              <span>Настройки</span>
              <Icons.ChevronRight className={`w-3 h-3 transition-transform ${isExpanded ? 'rotate-90' : ''}`} />
            </button>
          )}
        </div>
        {status === 'current' && (
          <button className="p-1.5 text-stone-400 hover:text-orange-600 hover:bg-orange-50 rounded transition-colors" onClick={(e) => e.stopPropagation()}>
            <Icons.RefreshCw className="w-4 h-4" />
          </button>
        )}
      </div>
      {isExpanded && status === 'current' && stepConfig?.hasSettings && <SettingsPanel step={step.id} onRerun={() => {}} />}
    </div>
  );
}

// ============================================================================
// MAIN COMPONENT
// ============================================================================
export default function StepByStepFinal() {
  const [completedSteps, setCompletedSteps] = useState(new Set(['parse', 'transcribe', 'clean', 'longread', 'summarize', 'chunk']));
  const [isLoading, setIsLoading] = useState(false);
  const [activeResultTab, setActiveResultTab] = useState('chunks');
  const [expandedSettings, setExpandedSettings] = useState(null);
  const [processingStep, setProcessingStep] = useState(null);
  const [progress, setProgress] = useState(0);
  const [showCleanedDiff, setShowCleanedDiff] = useState(false);
  const [showLongreadDiff, setShowLongreadDiff] = useState(false);

  const totals = useMemo(() => calculateTotals(MOCK_RESULTS), []);

  const { nextStep, currentStepIndex } = useMemo(() => {
    let nextPending = null;
    let currentIdx = -1;
    for (let i = 0; i < STEPS.length; i++) {
      if (completedSteps.has(STEPS[i].id)) currentIdx = i;
      else if (!nextPending) nextPending = STEPS[i].id;
    }
    return { nextStep: nextPending, currentStepIndex: currentIdx };
  }, [completedSteps]);

  const getStepStatus = (step, index) => {
    if (completedSteps.has(step)) return index === currentStepIndex ? 'current' : 'completed';
    if (step === nextStep) return 'next';
    return 'pending';
  };

  const availableTabs = useMemo(() => {
    return STEPS.filter(s => completedSteps.has(s.id) && s.resultTab).map(s => ({ id: s.resultTab, label: s.shortLabel, icon: s.icon }));
  }, [completedSteps]);

  const handleExecuteStep = () => {
    setIsLoading(true);
    setProcessingStep(nextStep);
    setProgress(0);
    const interval = setInterval(() => { setProgress(prev => prev >= 100 ? 100 : prev + Math.random() * 15); }, 200);
    setTimeout(() => {
      clearInterval(interval);
      setCompletedSteps(prev => new Set([...prev, nextStep]));
      setIsLoading(false);
      setProcessingStep(null);
      setProgress(0);
      const stepConfig = STEPS.find(s => s.id === nextStep);
      if (stepConfig?.resultTab) setActiveResultTab(stepConfig.resultTab);
    }, 2000);
  };

  useEffect(() => { setShowCleanedDiff(false); setShowLongreadDiff(false); }, [activeResultTab]);

  const allCompleted = !nextStep;

  const renderResultContent = () => {
    switch (activeResultTab) {
      case 'metadata': return <MetadataResultContent data={MOCK_RESULTS.metadata} />;
      case 'rawTranscript': return <TranscriptResultContent data={MOCK_RESULTS.rawTranscript} />;
      case 'cleanedTranscript': return <CleanedTranscriptResultContent data={MOCK_RESULTS.cleanedTranscript} rawData={MOCK_RESULTS.rawTranscript} showDiff={showCleanedDiff} onToggleDiff={() => setShowCleanedDiff(!showCleanedDiff)} />;
      case 'longread': return <LongreadResultContent data={MOCK_RESULTS.longread} cleanedData={MOCK_RESULTS.cleanedTranscript} showDiff={showLongreadDiff} onToggleDiff={() => setShowLongreadDiff(!showLongreadDiff)} />;
      case 'summary': return <SummaryResultContent data={MOCK_RESULTS.summary} />;
      case 'chunks': return <ChunksResultContent data={MOCK_RESULTS.chunks} />;
      default: return null;
    }
  };

  return (
    <div className="flex flex-col h-screen bg-stone-100">
      <header className="flex items-center justify-between px-6 py-4 bg-white border-b border-stone-200 flex-shrink-0">
        <div className="flex flex-col gap-0.5">
          <span className="text-xs font-semibold uppercase tracking-wider text-stone-400">Пошаговая обработка</span>
          <h1 className="text-lg font-medium text-stone-900">2026.01 Форум Табтим. Тестовая тема (Светлана Дмитрук).mp3</h1>
        </div>
        <button className="px-4 py-2 text-sm font-medium text-stone-600 bg-transparent border border-stone-300 rounded-lg hover:bg-stone-50 transition-colors">Отменить</button>
      </header>
      <div className="flex flex-1 overflow-hidden min-h-0">
        <aside className="w-80 flex flex-col gap-5 p-5 bg-white border-r border-stone-200 overflow-y-auto flex-shrink-0">
          {isLoading ? (
            <ProgressIndicator step={processingStep} progress={Math.min(Math.round(progress), 100)} elapsed="5с" eta="~8с" status="Обработка..." />
          ) : allCompleted ? (
            <CompletionCard files={MOCK_RESULTS.save.files} totals={totals} onClose={() => {}} />
          ) : (
            <NextStepCard step={nextStep} stepIndex={currentStepIndex + 1} onExecute={handleExecuteStep} />
          )}
          <div className="flex-1">
            <h4 className="text-xs font-semibold uppercase tracking-wider text-stone-400 mb-3">Этапы обработки</h4>
            <div className="flex flex-col">
              {STEPS.map((step, index) => (
                <TimelineStep key={step.id} step={step} index={index} status={getStepStatus(step.id, index)} isExpanded={expandedSettings === step.id} onToggleSettings={() => setExpandedSettings(expandedSettings === step.id ? null : step.id)} onSelect={() => { if (step.resultTab) setActiveResultTab(step.resultTab); }} totalSteps={STEPS.length} />
              ))}
            </div>
          </div>
        </aside>
        <main className="flex-1 flex flex-col bg-stone-100 overflow-hidden min-h-0">
          {availableTabs.length > 0 ? (
            <>
              <div className="flex gap-1 px-5 py-3 bg-white border-b border-stone-200 overflow-x-auto flex-shrink-0">
                {availableTabs.map(tab => {
                  const Icon = Icons[tab.icon];
                  return (
                    <button key={tab.id} className={`flex items-center gap-1.5 px-3.5 py-2 text-sm font-medium rounded-lg whitespace-nowrap transition-all ${activeResultTab === tab.id ? 'text-blue-600 bg-blue-50 border border-blue-200' : 'text-stone-500 hover:text-stone-700 hover:bg-stone-50 border border-transparent'}`} onClick={() => setActiveResultTab(tab.id)}>
                      <Icon className="w-4 h-4" />
                      <span>{tab.label}</span>
                    </button>
                  );
                })}
              </div>
              <div className="flex-1 p-5 min-h-0">{renderResultContent()}</div>
            </>
          ) : (
            <div className="flex-1 flex flex-col items-center justify-center text-stone-400">
              <Icons.FileText className="w-12 h-12 mb-3 opacity-40" />
              <p>Результаты появятся после выполнения первого шага</p>
            </div>
          )}
        </main>
      </div>
    </div>
  );
}
