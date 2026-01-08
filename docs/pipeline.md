# Pipeline обработки видео

> Детальное описание этапов обработки видео от inbox до готовых файлов для БЗ 2.0.

## Обзор Pipeline

```
┌─────────────────────────────────────────────────────────────────┐
│                      VIDEO PROCESSING PIPELINE                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐       │
│  │ 1.PARSE │───▶│2.WHISPER│───▶│3.CLEAN  │───▶│4.CHUNK  │       │
│  │ filename│    │transcr. │    │ + gloss │    │semantic │       │
│  └─────────┘    └─────────┘    └─────────┘    └─────────┘       │
│                                                   │             │
│                                                   ▼             │
│                              ┌─────────┐    ┌─────────┐         │
│                              │6.SAVE   │◀───│5.SUMMAR.│         │
│                              │ files   │    │ + class │         │
│                              └─────────┘    └─────────┘         │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Краткое описание этапов

| Этап | Название | Инструмент | Вход | Выход |
|------|----------|------------|------|-------|
| 1 | Parse Filename | Python regex | `*.mp4` filename | `VideoMetadata` |
| 2 | Transcribe | faster-whisper | `*.mp4` file | `RawTranscript` |
| 3 | Clean | Ollama + Glossary | `RawTranscript` | `CleanedTranscript` |
| 4 | Chunk | Ollama | `CleanedTranscript` | `TranscriptChunks` |
| 5 | Summarize | Ollama | `CleanedTranscript` | `Summary` + classification |
| 6 | Save | Python | All data | Files in archive |

---

## Этап 1: Parse Filename

### Назначение

Извлечение метаданных из имени файла по установленному паттерну.

### Паттерн имени файла

```
{дата} {тип}.{поток} {тема} ({спикер}).mp4

Пример:
2025.04.07 ПШ.SV Подготовка и проведение Группы поддержки (Светлана Дмитрук).mp4
```

### Regex

```python
FILENAME_PATTERN = r'^(\d{4}\.\d{2}\.\d{2})\s+(\w+)\.(\w+)\s+(.+?)\s+\(([^)]+)\)(?:\.\w+)?$'

# Группы:
# 1: date       (2025.04.07)
# 2: event_type (ПШ)
# 3: stream     (SV)
# 4: title      (Подготовка и проведение Группы поддержки)
# 5: speaker    (Светлана Дмитрук)
```

### Модель данных

```python
from dataclasses import dataclass
from datetime import date
from pathlib import Path

@dataclass
class VideoMetadata:
    """Метаданные видео, извлечённые из имени файла."""
    
    # Из имени файла
    date: date                    # 2025-04-07
    event_type: str               # ПШ
    stream: str                   # SV
    title: str                    # Подготовка и проведение Группы поддержки
    speaker: str                  # Светлана Дмитрук
    
    # Вычисляемые
    original_filename: str        # Полное имя файла
    video_id: str                 # 2025-04-07_psh-sv_gruppa-podderzhki
    
    # Пути
    source_path: Path             # /inbox/filename.mp4
    archive_path: Path            # /archive/2025/04/ПШ.SV/Title (Speaker)/
    
    @property
    def stream_full(self) -> str:
        """Полное название потока из config/events.yaml."""
        # ПШ.SV -> Понедельничная Школа — Супервайзеры
        pass
```

### Генерация video_id

```python
def generate_video_id(metadata: VideoMetadata) -> str:
    """
    Генерирует уникальный ID для видео.
    
    Формат: {date}_{event_type}-{stream}_{slug}
    Пример: 2025-04-07_psh-sv_gruppa-podderzhki
    """
    date_str = metadata.date.isoformat()  # 2025-04-07
    event_stream = f"{metadata.event_type}-{metadata.stream}".lower()  # psh-sv
    slug = slugify(metadata.title)  # gruppa-podderzhki
    
    return f"{date_str}_{event_stream}_{slug}"
```

### Error Handling

```python
class FilenameParseError(Exception):
    """Имя файла не соответствует паттерну."""
    pass

def parse_filename(filename: str) -> VideoMetadata:
    match = re.match(FILENAME_PATTERN, filename)
    if not match:
        raise FilenameParseError(
            f"Файл '{filename}' не соответствует паттерну. "
            f"Ожидается: '{{дата}} {{тип}}.{{поток}} {{тема}} ({{спикер}}).mp4'"
        )
    # ...
```

---

## Этап 2: Transcribe (Whisper)

### Назначение

Преобразование аудио в текст с сохранением временных меток сегментов.

### Инструмент

**faster-whisper-server** — REST API сервер для транскрипции, развёрнутый на TrueNAS.

| Параметр | Значение |
|----------|----------|
| API URL | http://100.64.0.1:9000 |
| Модель | large-v3 (предзагружена) |
| GPU | RTX 5070 Ti |

### Конфигурация

```python
import requests

WHISPER_CONFIG = {
    "api_url": "http://100.64.0.1:9000",
    "language": "ru",              # Русский язык
    "response_format": "verbose_json",  # JSON с таймкодами
    "timeout": 600,                # 10 минут для длинных видео
}
````

### Модель данных

```python
@dataclass
class TranscriptSegment:
    """Один сегмент транскрипции от Whisper."""
    
    start: float          # Начало в секундах (15.5)
    end: float            # Конец в секундах (18.2)
    text: str             # Текст сегмента
    
    @property
    def start_time(self) -> str:
        """Форматированное время начала (00:00:15)."""
        return self._format_time(self.start)
    
    @property
    def end_time(self) -> str:
        """Форматированное время конца (00:00:18)."""
        return self._format_time(self.end)
    
    @staticmethod
    def _format_time(seconds: float) -> str:
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        return f"{h:02d}:{m:02d}:{s:02d}"


@dataclass
class RawTranscript:
    """Сырой транскрипт от Whisper."""
    
    segments: list[TranscriptSegment]
    language: str                    # Определённый язык
    duration_seconds: float          # Длительность видео
    whisper_model: str               # Использованная модель
    
    @property
    def full_text(self) -> str:
        """Полный текст без тайм-кодов."""
        return " ".join(seg.text for seg in self.segments)
    
    @property
    def text_with_timestamps(self) -> str:
        """Текст с тайм-кодами для LLM обработки."""
        lines = []
        for seg in self.segments:
            lines.append(f"[{seg.start_time}] {seg.text}")
        return "\n".join(lines)
```

### Процесс транскрипции

```python
import requests
from pathlib import Path

async def transcribe(video_path: Path, config: dict) -> RawTranscript:
    """
    Транскрибирует видео через Whisper HTTP API.
    
    1. Отправляет файл на сервер faster-whisper
    2. Получает JSON с сегментами и метаданными
    3. Собирает сегменты в RawTranscript
    """
    
    url = f"{config['api_url']}/v1/audio/transcriptions"
    
    with open(video_path, "rb") as f:
        response = requests.post(
            url,
            files={"file": f},
            data={
                "language": config["language"],
                "response_format": config["response_format"],
            },
            timeout=config["timeout"]
        )
    
    response.raise_for_status()
    data = response.json()
    
    # Парсинг сегментов из ответа API
    transcript_segments = [
        TranscriptSegment(
            start=seg["start"],
            end=seg["end"],
            text=seg["text"].strip()
        )
        for seg in data.get("segments", [])
    ]
    
    return RawTranscript(
        segments=transcript_segments,
        language=data.get("language", config["language"]),
        duration_seconds=data.get("duration", 0),
        whisper_model="large-v3"
    )
```

### Альтернатива: простой текст без сегментов

```python
async def transcribe_text_only(video_path: Path, config: dict) -> str:
    """
    Быстрая транскрипция — только текст без таймкодов.
    Используй когда сегменты не нужны.
    """
    
    url = f"{config['api_url']}/v1/audio/transcriptions"
    
    with open(video_path, "rb") as f:
        response = requests.post(
            url,
            files={"file": f},
            data={
                "language": config["language"],
                "response_format": "text",
            },
            timeout=config["timeout"]
        )
    
    response.raise_for_status()
    return response.text
```

### Прогресс транскрипции

```python
# WebSocket updates для UI
async def transcribe_with_progress(
    video_path: Path,
    config: dict,
    progress_callback: Callable[[float, str], None]
) -> RawTranscript:
    """
    Транскрипция с обновлениями прогресса.
    
    progress_callback(percent, status_message)
    
    Примечание: Whisper API не возвращает прогресс в реальном времени.
    Прогресс оценивается по этапам: отправка → обработка → готово.
    """
    progress_callback(0, "Подготовка файла...")
    
    # Оценка времени по размеру файла
    file_size_mb = video_path.stat().st_size / (1024 * 1024)
    estimated_seconds = file_size_mb * 0.5  # ~0.5 сек на MB (эмпирически)
    
    progress_callback(5, "Отправка на сервер Whisper...")
    
    url = f"{config['api_url']}/v1/audio/transcriptions"
    
    with open(video_path, "rb") as f:
        progress_callback(10, f"Транскрипция (~{int(estimated_seconds)} сек)...")
        
        response = requests.post(
            url,
            files={"file": f},
            data={
                "language": config["language"],
                "response_format": config["response_format"],
            },
            timeout=config["timeout"]
        )
    
    progress_callback(90, "Обработка результата...")
    
    response.raise_for_status()
    data = response.json()
    
    transcript_segments = [
        TranscriptSegment(
            start=seg["start"],
            end=seg["end"],
            text=seg["text"].strip()
        )
        for seg in data.get("segments", [])
    ]
    
    progress_callback(100, "Транскрипция завершена")
    
    return RawTranscript(
        segments=transcript_segments,
        language=data.get("language", config["language"]),
        duration_seconds=data.get("duration", 0),
        whisper_model="large-v3"
    )
```

### Проверка доступности сервиса

```python
def check_whisper_available(config: dict) -> bool:
    """Проверить что Whisper сервис доступен."""
    try:
        response = requests.get(
            f"{config['api_url']}/health",
            timeout=5
        )
        return response.text == "OK"
    except requests.RequestException:
        return False
```

### Производительность

|Метрика|Значение|
|---|---|
|Модель|large-v3 (предзагружена на сервере)|
|Первый запрос после простоя|~65 сек (загрузка модели в VRAM)|
|Последующие запросы|~4-5 сек на 15 сек аудио|
|VRAM|~3.5 GB|
|Таймаут модели|5 мин неактивности|

> **Важно:** Первый запрос после простоя сервера будет медленным — модель загружается в GPU память. Последующие запросы выполняются быстро.

---

## Этап 3: Clean (LLM + Glossary)

### Назначение

Очистка сырого транскрипта от шума и нормализация терминологии.

### Проблемы сырого транскрипта

| Проблема | Пример | Решение |
|----------|--------|---------|
| Слова-паразиты | "ну", "вот", "как бы", "эээ" | LLM удаляет |
| Отвлечения | "кстати, вчера я..." | LLM удаляет |
| Ошибки Whisper | "Формула один" | Глоссарий исправляет |
| Термины Herbalife | "гербалайф" | Глоссарий нормализует |

### Двухэтапная очистка

```
RawTranscript
     │
     ▼
┌─────────────────┐
│ 3a. GLOSSARY    │  Быстрая замена по словарю
│    (Python)     │  
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 3b. LLM CLEAN   │  Удаление паразитов и отвлечений
│    (Ollama)     │  
└────────┬────────┘
         │
         ▼
  CleanedTranscript
```

### 3a. Применение глоссария

```python
import yaml
import re
from pathlib import Path

def load_glossary(path: Path = Path("config/glossary.yaml")) -> dict:
    """Загружает глоссарий терминов."""
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def apply_glossary(text: str, glossary: dict) -> str:
    """
    Заменяет вариации терминов на каноническую форму.
    
    Порядок важен: сначала длинные фразы, потом короткие.
    """
    replacements = []
    
    # Собираем все замены из всех категорий
    for category in glossary.values():
        for term in category:
            canonical = term["canonical"]
            for variation in term["variations"]:
                replacements.append((variation, canonical))
    
    # Сортируем по длине (длинные первыми)
    replacements.sort(key=lambda x: len(x[0]), reverse=True)
    
    # Применяем замены
    for variation, canonical in replacements:
        # Regex с границами слов, регистронезависимо
        pattern = rf'\b{re.escape(variation)}\b'
        text = re.sub(pattern, canonical, text, flags=re.IGNORECASE)
    
    return text
```

### Структура glossary.yaml

```yaml
# config/glossary.yaml

products:
  - canonical: "Формула 1"
    variations:
      - "формула один"
      - "формула 1"
      - "Ф1"
      - "ф-1"
      - "formula 1"
      - "formula one"
  
  - canonical: "Формула 2"
    variations:
      - "формула два"
      - "формула 2"
      - "Ф2"
      - "ф-2"
  
  - canonical: "Протеиновая смесь"
    variations:
      - "протеин микс"
      - "протеин шейк"
      - "protein mix"
      - "белковая смесь"

brand:
  - canonical: "Herbalife"
    variations:
      - "гербалайф"
      - "гербо лайф"
      - "хербалайф"
      - "herbal life"
      - "херба лайф"

business:
  - canonical: "Группа поддержки"
    variations:
      - "группа поддержки"
      - "гп"
      - "групповая поддержка"
  
  - canonical: "Понедельничная Школа"
    variations:
      - "понедельничная школа"
      - "пш"
      - "школа понедельника"
      - "monday school"

roles:
  - canonical: "Супервайзер"
    variations:
      - "супервайзер"
      - "супервизор"
      - "св"
      - "supervisor"
  
  - canonical: "Независимый партнёр"
    variations:
      - "независимый партнер"
      - "нп"
      - "партнер"
      - "independent partner"
```

### 3b. LLM Clean (Ollama)

```python
from ollama import AsyncClient

LLM_CLEAN_CONFIG = {
    "model": "qwen2.5:14b",
    "temperature": 0.3,          # Низкая для консистентности
    "num_ctx": 16384,            # Большой контекст для длинных транскриптов
}

async def llm_clean_transcript(
    text: str,
    metadata: VideoMetadata,
    client: AsyncClient
) -> str:
    """
    Очищает транскрипт через LLM.
    
    Удаляет:
    - Слова-паразиты
    - Отвлечения от темы
    - Повторы и заикания
    
    Сохраняет:
    - Весь смысловой контент
    - Структуру изложения
    """
    
    prompt = load_prompt("config/prompts/cleaner.md")
    prompt = prompt.format(
        title=metadata.title,
        speaker=metadata.speaker,
        transcript=text
    )
    
    response = await client.chat(
        model="qwen2.5:14b",
        messages=[{"role": "user", "content": prompt}],
        options={
            "temperature": LLM_CLEAN_CONFIG["temperature"],
            "num_ctx": LLM_CLEAN_CONFIG["num_ctx"],
        }
    )
    
    return response["message"]["content"]
```

### Промпт очистки (config/prompts/cleaner.md)

```markdown
Ты — редактор транскриптов обучающих видео.

**Видео:** {title}
**Спикер:** {speaker}

**Твоя задача — очистить транскрипт:**

1. **Удали слова-паразиты:**
   - "ну", "вот", "как бы", "типа", "значит"
   - "эээ", "ммм", "ааа" и подобные
   - Избыточные "то есть", "так сказать"

2. **Удали отвлечения от темы:**
   - Личные истории, не относящиеся к теме
   - Организационные моменты ("подождите, сейчас настрою")
   - Приветствия и прощания (если не несут смысла)

3. **Исправь очевидные ошибки речи:**
   - Оборванные предложения — заверши или удали
   - Повторы слов — оставь один раз
   - Самокоррекции ("нет, не так, а вот так") — оставь финальный вариант

4. **СОХРАНИ:**
   - Весь смысловой контент
   - Примеры и истории по теме
   - Структуру изложения
   - Профессиональную терминологию

**Транскрипт для очистки:**

{transcript}

**Ответ:**
Очищенный транскрипт (только текст, без комментариев):
```

### Модель данных

```python
@dataclass
class CleanedTranscript:
    """Очищенный транскрипт."""
    
    text: str                         # Очищенный текст
    original_length: int              # Длина до очистки (символы)
    cleaned_length: int               # Длина после очистки
    glossary_replacements: int        # Количество замен по глоссарию
    
    @property
    def reduction_percent(self) -> float:
        """Процент сокращения текста."""
        return (1 - self.cleaned_length / self.original_length) * 100
```

---

## Этап 4: Chunk (Semantic Splitting)

### Назначение

Разбиение очищенного транскрипта на смысловые блоки для RAG.

### Принципы chunking

| Критерий | Значение | Почему |
|----------|----------|--------|
| Размер chunk | 100-400 слов | Оптимально для embeddings |
| Смысловая завершённость | Одна тема/мысль | Chunk понятен без контекста |
| Overlap | Не требуется | Очищенный текст структурирован |

### LLM Chunking (Ollama)

```python
async def chunk_transcript(
    cleaned_text: str,
    metadata: VideoMetadata,
    client: AsyncClient
) -> list[dict]:
    """
    Разбивает транскрипт на смысловые блоки через LLM.
    
    Returns:
        List of chunks with topic and text
    """
    
    prompt = load_prompt("config/prompts/chunker.md")
    prompt = prompt.format(
        title=metadata.title,
        transcript=cleaned_text
    )
    
    response = await client.chat(
        model="qwen2.5:14b",
        messages=[{"role": "user", "content": prompt}],
        options={"temperature": 0.3},
        format="json"  # Запрашиваем JSON ответ
    )
    
    return json.loads(response["message"]["content"])["chunks"]
```

### Промпт chunking (config/prompts/chunker.md)

```markdown
Разбей транскрипт на смысловые блоки для поисковой системы.

**Видео:** {title}

**Требования к блокам:**
1. Каждый блок — одна законченная тема или мысль
2. Размер блока: 100-400 слов
3. Блок должен быть понятен без контекста других блоков
4. Сохрани весь контент, ничего не удаляй

**Транскрипт:**

{transcript}

**Формат ответа (JSON):**

```json
{
  "chunks": [
    {
      "index": 1,
      "topic": "Краткая тема блока (3-7 слов)",
      "text": "Полный текст блока..."
    },
    {
      "index": 2,
      "topic": "...",
      "text": "..."
    }
  ]
}
```

**Ответ:**
```

### Модель данных

```python
@dataclass
class TranscriptChunk:
    """Один смысловой блок транскрипта."""
    
    id: str                # {video_id}_{index:03d}
    index: int             # Порядковый номер (1, 2, 3...)
    topic: str             # Краткая тема блока
    text: str              # Текст блока
    word_count: int        # Количество слов
    
    # Опционально (для будущего расширения)
    # start_time: str | None = None
    # end_time: str | None = None


@dataclass 
class TranscriptChunks:
    """Результат chunking."""
    
    video_id: str
    chunks: list[TranscriptChunk]
    total_chunks: int
    avg_chunk_size: int              # Средний размер в словах
```

---

## Этап 5: Summarize (+ Classification)

### Назначение

Создание структурированного саммари для File Search в БЗ 2.0.

### LLM Summarization

```python
async def summarize_transcript(
    cleaned_text: str,
    metadata: VideoMetadata,
    client: AsyncClient
) -> dict:
    """
    Создаёт саммари и классификацию для БЗ 2.0.
    
    Returns:
        {
            "summary": "...",
            "key_points": [...],
            "recommendations": [...],
            "target_audience": "...",
            "classification": {
                "section": "...",
                "subsection": "...",
                "tags": [...]
            }
        }
    """
    
    prompt = load_prompt("config/prompts/summarizer.md")
    prompt = prompt.format(
        title=metadata.title,
        speaker=metadata.speaker,
        date=metadata.date.strftime("%d %B %Y"),
        stream=metadata.stream_full,
        transcript=cleaned_text
    )
    
    response = await client.chat(
        model="qwen2.5:14b",
        messages=[{"role": "user", "content": prompt}],
        options={"temperature": 0.5},
        format="json"
    )
    
    return json.loads(response["message"]["content"])
```

### Промпт саммаризации (config/prompts/summarizer.md)

```markdown
Создай саммари обучающего видео для базы знаний консультантов Herbalife.

**Метаданные:**
- Тема: {title}
- Спикер: {speaker}
- Дата: {date}
- Поток: {stream}

**Транскрипт:**

{transcript}

**Создай структурированное саммари в JSON:**

```json
{
  "summary": "2-3 абзаца: о чём видео и какую проблему решает",
  
  "key_points": [
    "Ключевой тезис 1",
    "Ключевой тезис 2",
    "Ключевой тезис 3"
  ],
  
  "recommendations": [
    "Практическая рекомендация 1",
    "Практическая рекомендация 2",
    "Практическая рекомендация 3"
  ],
  
  "target_audience": "Для кого полезно это видео",
  
  "classification": {
    "section": "Один из: Обучение | Продукты | Бизнес | Мотивация",
    "subsection": "Подкатегория внутри секции",
    "tags": ["тег1", "тег2", "тег3", "тег4", "тег5"],
    "access_level": 1
  },
  
  "questions_answered": [
    "На какой вопрос отвечает видео 1?",
    "На какой вопрос отвечает видео 2?",
    "На какой вопрос отвечает видео 3?"
  ]
}
```

**Ответ:**
```

### Модель данных

```python
@dataclass
class VideoSummary:
    """Саммари видео для БЗ 2.0."""
    
    # Контент
    summary: str                      # Краткое содержание
    key_points: list[str]             # Ключевые тезисы
    recommendations: list[str]        # Практические рекомендации
    target_audience: str              # Для кого полезно
    questions_answered: list[str]     # Вопросы, на которые отвечает
    
    # Классификация
    section: str                      # Обучение / Продукты / Бизнес / Мотивация
    subsection: str                   # Подкатегория
    tags: list[str]                   # Теги для поиска
    access_level: int                 # Уровень доступа (1-4)
```

---

## Этап 6: Save Files

### Назначение

Сохранение результатов обработки в структурированный архив.

### Структура архива

```
/archive/
└── {год}/
    └── {месяц}/
        └── {тип}.{поток}/
            └── {тема} ({спикер})/
                ├── {original_filename}.mp4      # Видео
                ├── transcript_chunks.json       # Для RAG
                ├── summary.md                   # Для File Search
                └── transcript_raw.txt           # Backup оригинала
```

### Генерация transcript_chunks.json

```python
def save_transcript_chunks(
    video_id: str,
    metadata: VideoMetadata,
    raw_transcript: RawTranscript,
    chunks: TranscriptChunks,
    archive_path: Path
) -> Path:
    """
    Сохраняет chunks в JSON для RAG-индексации.
    """
    
    data = {
        "video_id": video_id,
        "metadata": {
            "title": metadata.title,
            "speaker": metadata.speaker,
            "date": metadata.date.isoformat(),
            "stream": metadata.stream,
            "stream_name": metadata.stream_full,
            "duration_seconds": raw_transcript.duration_seconds,
            "language": raw_transcript.language,
            "whisper_model": raw_transcript.whisper_model,
            "processed_at": datetime.now().isoformat(),
        },
        "chunks": [
            {
                "id": chunk.id,
                "index": chunk.index,
                "topic": chunk.topic,
                "text": chunk.text,
                "word_count": chunk.word_count,
            }
            for chunk in chunks.chunks
        ],
        "statistics": {
            "total_chunks": chunks.total_chunks,
            "avg_chunk_size": chunks.avg_chunk_size,
        }
    }
    
    output_path = archive_path / "transcript_chunks.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    return output_path
```

### Генерация summary.md

```python
def save_summary_md(
    video_id: str,
    metadata: VideoMetadata,
    raw_transcript: RawTranscript,
    summary: VideoSummary,
    archive_path: Path
) -> Path:
    """
    Генерирует summary.md с YAML frontmatter для БЗ 2.0.
    """
    
    # Форматирование длительности
    duration = format_duration(raw_transcript.duration_seconds)
    
    content = f'''---
# === Идентификация ===
video_id: "{video_id}"
title: "{metadata.title}"
type: "video_summary"

# === Источник ===
speaker: "{metadata.speaker}"
date: "{metadata.date.isoformat()}"
stream: "{metadata.stream}"
stream_name: "{metadata.stream_full}"
duration: "{duration}"

# === Классификация для БЗ 2.0 ===
section: "{summary.section}"
subsection: "{summary.subsection}"
access_level: {summary.access_level}
tags:
{format_yaml_list(summary.tags)}

# === Ссылки ===
transcript_file: "transcript_chunks.json"

# === Служебное ===
created: "{datetime.now().isoformat()}"
llm_model: "qwen2.5:14b"
---

# {metadata.title}

**Спикер:** {metadata.speaker}  
**Дата:** {metadata.date.strftime("%d %B %Y")}  
**Поток:** {metadata.stream_full}

---

## Краткое содержание

{summary.summary}

## Ключевые тезисы

{format_bullet_list(summary.key_points)}

## Практические рекомендации

{format_numbered_list(summary.recommendations)}

## Для кого полезно

{summary.target_audience}

## Вопросы, на которые отвечает видео

{format_bullet_list(summary.questions_answered)}

---

📝 **Полная транскрипция:** доступна в базе знаний
'''
    
    output_path = archive_path / "summary.md"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)
    
    return output_path
```

### Сохранение raw транскрипта (backup)

```python
def save_raw_transcript(
    raw_transcript: RawTranscript,
    archive_path: Path
) -> Path:
    """
    Сохраняет оригинальный транскрипт с тайм-кодами.
    Backup на случай необходимости переобработки.
    """
    
    output_path = archive_path / "transcript_raw.txt"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(raw_transcript.text_with_timestamps)
    
    return output_path
```

---

## Полный Pipeline Flow

```python
async def process_video(video_path: Path) -> ProcessingResult:
    """
    Полный pipeline обработки видео.
    """
    
    # 1. Parse filename
    metadata = parse_filename(video_path.name)
    video_id = generate_video_id(metadata)
    
    # 2. Transcribe
    raw_transcript = await transcribe(video_path, WHISPER_CONFIG)
    
    # 3. Clean
    glossary = load_glossary()
    text_with_glossary = apply_glossary(raw_transcript.full_text, glossary)
    cleaned_text = await llm_clean_transcript(text_with_glossary, metadata)
    
    # 4. Chunk
    chunks = await chunk_transcript(cleaned_text, metadata)
    
    # 5. Summarize
    summary = await summarize_transcript(cleaned_text, metadata)
    
    # 6. Save
    archive_path = create_archive_path(metadata)
    
    # Перемещаем видео
    shutil.move(video_path, archive_path / video_path.name)
    
    # Сохраняем результаты
    save_transcript_chunks(video_id, metadata, raw_transcript, chunks, archive_path)
    save_summary_md(video_id, metadata, raw_transcript, summary, archive_path)
    save_raw_transcript(raw_transcript, archive_path)
    
    return ProcessingResult(
        video_id=video_id,
        archive_path=archive_path,
        chunks_count=len(chunks),
        duration=raw_transcript.duration_seconds,
    )
```

---

## Error Handling

### Типы ошибок

| Этап | Ошибка | Действие |
|------|--------|----------|
| 1. Parse | Неверный формат имени | Пропустить, уведомить |
| 2. Whisper | OOM (нехватка VRAM) | Retry с меньшей моделью |
| 2. Whisper | Corrupted video | Пропустить, уведомить |
| 3-5. LLM | Ollama недоступен | Retry с backoff |
| 3-5. LLM | Invalid JSON response | Retry (до 3 раз) |
| 6. Save | Disk full | Остановить pipeline |

### Retry логика

```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=60)
)
async def call_ollama_with_retry(prompt: str, **kwargs):
    """Вызов Ollama с автоматическим retry."""
    return await ollama_client.chat(...)
```

---

## Связанные документы

- [architecture.md](architecture.md) — схема системы, компоненты
- [data-formats.md](data-formats.md) — детальные форматы файлов
- [llm-prompts.md](llm-prompts.md) — все промпты с примерами
