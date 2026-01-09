# RFC: Оценочный прогресс обработки видео

**Статус:** Завершено
**Дата:** 2026-01-09
**Обновлено:** 2026-01-10
**Автор:** Claude + Roman

## Цель

Добавить оценочный индикатор прогресса (%) для всех длительных этапов обработки видео, чтобы пользователь видел что процесс идёт и примерно понимал сколько осталось.

## Проблема

При обработке видео (особенно транскрибации длинных файлов) UI показывал только статус этапа без индикации прогресса. Пользователь не знал, зависло ли приложение или процесс идёт нормально.

## Решение

Показывать оценочный % выполнения для каждого этапа на основе:
- Длительности видео (через ffprobe) для этапа транскрипции
- Количества символов текста для этапов очистки/чанкинга/суммаризации
- Коэффициентов производительности из `config/performance.yaml`
- Времени, прошедшего с начала этапа

Точность не критична — допустимо показать 90% когда реально 100%, или наоборот.

---

## Реализация (завершено 2026-01-10)

### 1. ProgressEstimator сервис

Файл: `backend/app/services/progress_estimator.py`

- Методы оценки времени: `estimate_transcribe()`, `estimate_clean()`, `estimate_chunk()`, `estimate_summarize()`
- Ticker с asyncio.Task: `start_ticker()`, `stop_ticker()`
- Загрузка коэффициентов из `config/performance.yaml`

### 2. Интеграция в pipeline.py

- `get_video_duration()` — получение длительности через ffprobe
- `duration_seconds` в `VideoMetadata`
- Ticker интегрирован во все `_do_*` методы
- `load_performance_config()` в `config.py`

### 3. Исправление блокировки event loop

**Проблема:** Ticker не обновлялся во время транскрипции — прогресс застревал.

**Причина:** httpx async client использовал синхронное чтение файла, блокируя event loop.

**Решение:** В `ai_client.py` метод `transcribe()` переработан:
- Выделен синхронный метод `_sync_transcribe()` для работы с файлом
- Вызывается через `asyncio.to_thread()` для выполнения в thread pool
- Event loop свободен для выполнения ticker

```python
# ai_client.py
def _sync_transcribe(self, file_path, language, whisper_url):
    with httpx.Client(timeout=7200.0) as sync_client:
        with open(file_path, "rb") as f:
            return sync_client.post(...)

async def transcribe(self, file_path, language=None):
    response = await asyncio.to_thread(
        self._sync_transcribe,
        file_path, language, self.settings.whisper_url
    )
```

### 4. Добавление ffmpeg в Docker

**Проблема:** Прогресс скакал с 22% на 47% при завершении транскрипции.

**Причина:** ffprobe отсутствовал в Docker образе. Длительность оценивалась по размеру файла:
- Оценка: `50MB / 83333 = 633s` (неверно)
- Реальная: `301s`

**Решение:** Добавлен ffmpeg в Dockerfile:
```dockerfile
RUN apt-get update && apt-get install -y curl ffmpeg && rm -rf /var/lib/apt/lists/*
```

**Результат:**
- До: 87s elapsed → 46% (оценка ~188s)
- После: 87s elapsed → 94% (оценка ~92s)

### 5. Балансировка весов этапов

**Проблема:** Прогресс достигал ~80% на суммаризации, затем скачок на 100% при сохранении.

**Причина:** Этап SAVING имел вес 12%, но выполнялся мгновенно (<1s).

**Решение:** Перераспределены веса по реальному времени выполнения:
- SAVING: 12% → 3% (мгновенный этап)
- TRANSCRIBING: 45% → 50% (основной по времени)
- CHUNK+SUMMARIZE: 26% → 32% (увеличены для плавности)

### 6. Step-by-Step режим

Не поддерживает прогресс — HTTP endpoints не могут отправлять промежуточные обновления.
Прогресс работает только в Full Pipeline режиме через WebSocket.

---

## Архитектура

### Файлы

| Файл | Статус | Описание |
|------|--------|----------|
| `backend/Dockerfile` | Готов | ffmpeg для ffprobe |
| `config/performance.yaml` | Готов | Коэффициенты оценки времени |
| `backend/app/config.py` | Готов | `load_performance_config()` |
| `backend/app/models/schemas.py` | Готов | `duration_seconds` в VideoMetadata |
| `backend/app/services/progress_estimator.py` | Готов | ProgressEstimator + Ticker |
| `backend/app/services/pipeline.py` | Готов | `get_video_duration()`, ticker в `_do_*` |
| `backend/app/services/ai_client.py` | Готов | `asyncio.to_thread()` для транскрипции |
| `frontend/.../FullPipeline.tsx` | Готов | Отображает `progress.progress` |

### Поток данных

```
Pipeline.process()
  │
  ├─ parse
  │   ├─ get_video_duration(ffprobe) → metadata.duration_seconds
  │   └─ fallback: file_size / 83333 (если ffprobe недоступен)
  │
  ├─ _do_transcribe(duration)
  │   ├─ estimator.estimate_transcribe(duration) → ~92s для 5-мин видео
  │   ├─ estimator.start_ticker() → asyncio.Task (обновляет % каждую секунду)
  │   ├─ await transcriber.transcribe() → asyncio.to_thread() (не блокирует)
  │   └─ estimator.stop_ticker() → 100%
  │
  ├─ _do_clean(input_chars)
  │   └─ аналогично, оценка по количеству символов
  │
  ├─ _do_chunk_and_summarize(input_chars)
  │   └─ параллельное выполнение, один ticker на max(chunk_time, summarize_time)
  │
  └─ _do_save()
      └─ фиксированное время ~2s
```

### Веса этапов для общего прогресса

```python
# Сбалансированы по реальному времени выполнения
STAGE_WEIGHTS = {
    PARSING: 2,        # 0-2%: instant
    TRANSCRIBING: 50,  # 2-52%: dominant stage (~77% of time)
    CLEANING: 13,      # 52-65%
    CHUNKING: 16,      # 65-81%: parallel with SUMMARIZING
    SUMMARIZING: 16,   # 65-97%: combined = 32%
    SAVING: 3,         # 97-100%: instant
}
```

**Изменения v2 (2026-01-10):**
- TRANSCRIBING: 45% → 50% (основной этап)
- CHUNKING+SUMMARIZING: 26% → 32% (параллельные)
- SAVING: 12% → 3% (мгновенный, скачок уменьшен)

---

## Коэффициенты производительности

```yaml
# config/performance.yaml (v2, 2026-01-10)
transcribe:
  factor_per_video_second: 0.29  # 87s на 301s видео
  base_time: 5.0
  # Формула: 5 + duration * 0.29

clean:
  factor_per_1k_chars: 0.9      # v1: 1.8 → v2: 0.9
  base_time: 2.0
  # Формула: 2 + chars/1000 * 0.9

chunk:
  factor_per_1k_chars: 4.0      # v1: 6.0 → v2: 4.0
  base_time: 2.0

summarize:
  factor_per_1k_chars: 3.0      # v1: 10.0 → v2: 3.0
  base_time: 3.0

fixed_stages:
  parse: 1.0
  save: 2.0
```

**Обновление коэффициентов:** Ручное, на основе PERF логов.

### История калибровок

| Версия | Дата | Источник | clean | chunk | summarize |
|--------|------|----------|-------|-------|-----------|
| v1 | 2026-01-09 | Full Pipeline | 1.8 | 6.0 | 10.0 |
| v2 | 2026-01-10 | Step-by-Step SSE | 0.9 | 4.0 | 3.0 |

**Причина v2:** Step-by-Step тест показал что коэффициенты были завышены:
- clean: дошёл до 49% (завышен 2x)
- chunk: дошёл до 70% (завышен 1.4x)
- summarize: дошёл до 37% (завышен 2.7x)

---

## Тестовые данные

### v1 (2026-01-09, Full Pipeline)

**5-минутный файл (301s, 50.3MB):**

```
PERF | transcribe | size=50.3MB | duration=301s | time=87.0s
PERF | clean | input_chars=4535 | output_chars=1770 | time=7.5s
PERF | chunk | input_chars=1770 | chunks=11 | time=18.3s
PERF | summarize | input_chars=1770 | time=6.6s
```

### v2 (2026-01-10, Step-by-Step SSE)

**5-минутный файл (301s, 50.3MB):**

```
PERF | transcribe | size=50.3MB | duration=301s | time=87.0s
PERF | clean | input_chars=4535 | output_chars=1335 | time=6.0s
PERF | chunk | input_chars=1335 | chunks=6 | time=7.4s
PERF | summarize | input_chars=1335 | time=7.1s
```

**Логи ticker (v1):**
```
Ticker transcribing: 75.8% (tick #71, elapsed=70.0s)
...
Ticker transcribing: 94.2% (tick #88, elapsed=87.0s)
Transcription complete: 117 segments, duration: 301s, elapsed: 87.1s

Ticker cleaning: 9.8% (tick #2, elapsed=1.0s)
...
Ticker cleaning: 68.6% (tick #8, elapsed=7.0s)
Cleaning complete: 4535 -> 1770 chars

Ticker chunking: 4.8% (tick #1, elapsed=0.0s)
...
Ticker chunking: 87.0% (tick #19, elapsed=18.0s)
Chunking complete: 11 chunks
```

---

## Известные ограничения

### 1. ~~Step-by-Step без прогресса~~ (решено)

~~HTTP endpoints не могут отправлять промежуточные обновления.~~
~~Прогресс работает только в Full Pipeline режиме.~~

**Решено 2026-01-10:** Добавлен SSE прогресс для Step-by-Step режима.

### 2. Точность оценки

Коэффициенты откалиброваны на 5-минутных файлах. Для очень длинных или коротких файлов точность может отличаться.

### 3. Cleaner на длинных файлах

55-минутный файл: clean сократил текст с 29013 до 232 символов (99.2% reduction).
Это отдельная проблема, не связанная с прогрессом.

---

## Критерии завершения

- [x] ProgressEstimator создан и загружает коэффициенты
- [x] Pipeline интегрирует ticker во все этапы
- [x] Ticker обновляет прогресс (`asyncio.to_thread()`)
- [x] ffprobe работает в Docker (добавлен ffmpeg)
- [x] Веса этапов сбалансированы (SAVING 12% → 3%)
- [x] FullPipeline показывает плавный % прогресса
- [x] Протестировано на 5-минутном файле

---

## Step-by-Step SSE прогресс (добавлено 2026-01-10)

### Проблема

Step-by-Step режим не поддерживал прогресс — HTTP endpoints не могли отправлять промежуточные обновления.

### Решение

Добавлен SSE (Server-Sent Events) прогресс для всех долгих операций:
- `/api/step/transcribe` — SSE с прогрессом транскрипции
- `/api/step/clean` — SSE с прогрессом очистки
- `/api/step/chunk` — SSE с прогрессом чанкинга
- `/api/step/summarize` — SSE с прогрессом суммаризации

### Архитектура

```
POST /api/step/transcribe
         ↓
    StreamingResponse (text/event-stream)
         ↓
    ProgressEstimator.start_ticker() ← Тот же ProgressEstimator что в Full Pipeline
         ↓
    SSE callback → yield f"data: {json}\n\n"
         ↓
    await orchestrator.transcribe()
         ↓
    ProgressEstimator.stop_ticker()
         ↓
    yield f"data: {result_json}\n\n"
```

### Формат SSE событий

```json
// Прогресс
{"type": "progress", "status": "transcribing", "progress": 45.5, "message": "Transcribing: video.mp4"}

// Результат
{"type": "result", "data": {...}}

// Ошибка
{"type": "error", "error": "..."}
```

### Файлы

| Файл | Описание |
|------|----------|
| `backend/app/api/step_routes.py` | SSE endpoints с `run_with_sse_progress()` |
| `frontend/src/api/sse.ts` | SSE клиент `fetchWithProgress()` |
| `frontend/src/api/hooks/useSteps.ts` | React hooks с прогрессом |
| `frontend/src/components/processing/StepByStep.tsx` | UI с ProgressBar |

### Тестирование

```bash
# curl тест SSE
curl -N -X POST http://localhost:8801/api/step/clean \
  -H "Content-Type: application/json" \
  -d '{"raw_transcript": {...}, "metadata": {...}}'

# Ожидаемый вывод:
data: {"type": "progress", "status": "cleaning", "progress": 0.0, "message": "..."}
data: {"type": "progress", "status": "cleaning", "progress": 48.2, "message": "..."}
data: {"type": "result", "data": {...}}
```

---

## Команды для отладки

```bash
# Проверить ffprobe в Docker
docker exec bz2-transcriber ffprobe -version

# Логи с ticker
docker logs bz2-transcriber | grep -E "(Ticker|Started ticker)"

# PERF логи
docker logs bz2-transcriber | grep "PERF |"

# Деплой
./scripts/deploy.sh
```
