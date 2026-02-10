# План: Исправление парсинга аудиозаписей и унификация определения длительности

## Проблема 1: Парсинг метаданных для offsite файлов с датой

Файл `2026.01 Форум Табтим. Антоновы (Дмитрий и Юлия).mp3` не парсится, потому что:

- **REGULAR_EVENT_PATTERN** требует полную дату `YYYY.MM.DD` (в файле только `2026.01`)
- **OFFSITE_LEADERSHIP_PATTERN** требует начало с фамилии, а файл начинается с даты
- **OFFSITE_EDUCATIONAL_PATTERN** требует формат `Фамилия — Название`

**Решение:** Добавить новый паттерн `DATED_OFFSITE_PATTERN` с маркером `#` для историй:
- `YYYY.MM EventName. # Surname (Names).ext` → leadership (история)
- `YYYY.MM EventName. Topic (Speaker).ext` → educational (тема спикера)

Точка после названия мероприятия — разделитель. Символ `#` после точки — маркер истории.

**Примеры:**
- История: `2026.01 Форум Табтим. # Антоновы (Дмитрий и Юлия).mp3`
- Тема: `2026.01 Форум Табтим. Тестовая тема (Светлана Дмитрук).mp3`

## Проблема 2: Дублирование кода определения длительности

Функция `get_video_duration()` дублирована в двух файлах:
- [orchestrator.py:48-79](backend/app/services/pipeline/orchestrator.py#L48-L79)
- [parse_stage.py:16-45](backend/app/services/stages/parse_stage.py#L16-L45)

**Решение:** Вынести в общий модуль `media_utils.py`

---

## Этапы реализации

### Этап 1: Создать `backend/app/utils/media_utils.py`

```python
def get_media_duration(media_path: Path) -> float | None:
    """Get duration via ffprobe (works for mp3/mp4)."""

def estimate_duration_from_size(file_path: Path) -> float:
    """Fallback: ~5 MB/min для видео, ~1 MB/min для аудио."""

def is_audio_file(file_path: Path) -> bool:
def is_video_file(file_path: Path) -> bool:
```

### Этап 2: Обновить экспорты в `backend/app/utils/__init__.py`

Добавить экспорт функций из `media_utils.py`.

### Этап 3: Обновить `orchestrator.py` и `parse_stage.py`

Заменить локальные `get_video_duration()` на импорт из `app.utils`.

### Этап 4: Добавить новый паттерн в `backend/app/services/parser.py`

1. Добавить `DATED_OFFSITE_PATTERN` после строки 82:
```python
# История (leadership): "2026.01 Форум Табтим. # Антоновы (Дмитрий и Юлия).mp3"
# Тема (educational): "2026.01 Форум Табтим. Тестовая тема (Светлана Дмитрук).mp3"
DATED_OFFSITE_PATTERN = re.compile(
    r'^(\d{4}\.\d{2})\s+'     # Date: 2026.01
    r'([^.]+)\.\s*'           # Event: "Форум Табтим."
    r'(#\s*)?'                # Optional # marker for leadership
    r'(.+?)\s*'               # Content: "Антоновы" или "Тестовая тема"
    r'\(([^)]+)\)'            # Names: "(Дмитрий и Юлия)" или "(Светлана Дмитрук)"
    r'(?:\.\w+)?$',           # Extension
    re.UNICODE
)
```

2. Добавить `parse_dated_offsite_filename()`:
   - Если есть `#` → leadership (история)
   - Если нет `#` → educational (тема)

3. Добавить `_parse_dated_offsite_event()` — создаёт `VideoMetadata` для offsite с датой

4. Обновить `parse_filename()` — добавить проверку нового паттерна между regular и offsite

### Этап 5: Оптимизировать `audio_extractor.py`

Добавить проверку: если входной файл уже MP3, копировать вместо перекодирования.

### Этап 6: Добавить тесты в `parser.py`

- Test 14: `2026.01 Форум Табтим. # Антоновы (Дмитрий и Юлия).mp3` → leadership
- Test 15: `2026.01 Форум Табтим. Тестовая тема (Светлана Дмитрук).mp3` → educational

### Этап 7: Обновить фронтенд для поддержки аудио

1. **Создать `frontend/src/utils/fileUtils.ts`:**
```typescript
export const AUDIO_EXTENSIONS = ['mp3', 'wav', 'm4a', 'flac', 'aac', 'ogg'];
export function isAudioFile(filename: string): boolean {
  const ext = filename.split('.').pop()?.toLowerCase() ?? '';
  return AUDIO_EXTENSIONS.includes(ext);
}
```

2. **Обновить `VideoItem.tsx`:**
   - Импортировать `Music` из lucide-react
   - Использовать `isAudioFile()` для выбора иконки: `Film` → видео, `Music` → аудио

3. **Обновить `InboxList.tsx`:**
   - Изменить `({files.length} видео)` → `({files.length} файлов)` или умный подсчёт

4. **Обновить `ProcessingModal.tsx`:**
   - Изменить заголовок "Обработка видео" → "Обработка" (универсально)

### Этап 8: Обновить документацию

1. **`docs/pipeline/01-parse.md`** — добавить новый формат с датой и маркером `#`
2. **`config/events.yaml`** — добавить `dated_offsite_*` в `filename_patterns`
3. **`CLAUDE.md`** — минимальное обновление: добавить 2 строки примеров в таблицу "Определение типа по имени файла"
4. **`docs/data-formats.md`** — добавить новый паттерн и примеры

---

## Файлы для изменения

### Backend (6 файлов)

| Файл | Изменения |
|------|-----------|
| [backend/app/utils/media_utils.py](backend/app/utils/media_utils.py) | Создать (новый) — get_media_duration, estimate_duration_from_size |
| [backend/app/utils/__init__.py](backend/app/utils/__init__.py) | Добавить экспорты |
| [backend/app/services/parser.py](backend/app/services/parser.py) | Добавить DATED_OFFSITE_PATTERN + функции + тесты |
| [backend/app/services/pipeline/orchestrator.py](backend/app/services/pipeline/orchestrator.py) | Заменить get_video_duration на импорт |
| [backend/app/services/stages/parse_stage.py](backend/app/services/stages/parse_stage.py) | Заменить get_video_duration на импорт |
| [backend/app/services/audio_extractor.py](backend/app/services/audio_extractor.py) | Добавить оптимизацию для MP3 |

### Frontend (4 файла)

| Файл | Изменения |
|------|-----------|
| [frontend/src/utils/fileUtils.ts](frontend/src/utils/fileUtils.ts) | Создать (новый) — isAudioFile() |
| [frontend/src/components/inbox/VideoItem.tsx](frontend/src/components/inbox/VideoItem.tsx) | Добавить иконку Music для аудио |
| [frontend/src/components/inbox/InboxList.tsx](frontend/src/components/inbox/InboxList.tsx) | Изменить "видео" → "файлов" |
| [frontend/src/components/processing/ProcessingModal.tsx](frontend/src/components/processing/ProcessingModal.tsx) | Универсальный заголовок |

### Документация (4 файла)

| Файл | Изменения |
|------|-----------|
| [docs/pipeline/01-parse.md](docs/pipeline/01-parse.md) | Добавить dated offsite формат |
| [config/events.yaml](config/events.yaml) | Добавить filename_patterns |
| [CLAUDE.md](CLAUDE.md) | Минимально: +2 строки примеров в существующую таблицу |
| [docs/data-formats.md](docs/data-formats.md) | Добавить новый паттерн |

---

## Верификация

1. **Тесты парсера:**
   ```bash
   cd backend && source .venv/bin/activate
   python -m app.services.parser
   ```

2. **Проверка на сервере:**
   ```bash
   ./scripts/deploy.sh
   ```
   Затем в UI выбрать файлы:
   - `2026.01 Форум Табтим. # Антоновы (Дмитрий и Юлия).mp3` → должен распознаться как leadership
   - `2026.01 Форум Табтим. Тестовая тема (Светлана Дмитрук).mp3` → должен распознаться как educational

3. **Проверка длительности:** Убедиться что ffprobe корректно определяет длительность MP3 файлов.
