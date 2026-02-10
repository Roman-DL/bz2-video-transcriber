# План исправления багов + рефакторинг AI клиентов (v0.27)

## Исходные проблемы

1. **Inbox не показывает аудиофайлы** — фильтруются только видео расширения
2. **"Whisper URL not configured"** — неправильная инициализация `OllamaClient`

## Решение: Рефакторинг + исправление багов

Выделим `WhisperClient` в отдельный класс (Single Responsibility Principle).

---

## Новая архитектура AI клиентов

```
BaseAIClient (Protocol)
├── OllamaClient    → только LLM (generate, chat)
├── ClaudeClient    → только LLM (generate, chat)
└── WhisperClient   → только транскрибация (NEW)
```

---

## Часть 1: Изменения в коде

### 1.1 Новый файл: `backend/app/services/ai_clients/whisper_client.py`

Выделить из OllamaClient:
- `transcribe()`
- `_sync_transcribe()`
- `check_health()` для Whisper

### 1.2 Обновить `ollama_client.py`

- Удалить `transcribe()`, `_sync_transcribe()`
- Удалить параметры `whisper_url`, `default_language`
- Оставить только LLM методы

### 1.3 Обновить зависимости

| Файл | Изменение |
|------|-----------|
| `ai_clients/__init__.py` | Добавить экспорт WhisperClient |
| `services/transcriber.py` | OllamaClient → WhisperClient |
| `services/stages/transcribe_stage.py` | OllamaClient → WhisperClient |
| `pipeline/orchestrator.py` | Отдельные клиенты для Whisper и LLM |
| `api/routes.py` | Добавить аудио расширения |
| `main.py` | Отдельная проверка Whisper в lifespan |

---

## Часть 2: Обновление документации

### Высокий приоритет (обязательно)

| Документ | Что обновить |
|----------|--------------|
| `CLAUDE.md` | Секция "AI Clients" — разделить Ollama и Whisper |
| `docs/adr/004-ai-client-abstraction.md` | Добавить WhisperClient в архитектуру |
| `docs/pipeline/02-transcribe.md` | Обновить диаграмму и примеры кода |
| `docs/api-reference.md` | Раздел "AI клиенты" — новая структура |

### Средний приоритет (желательно)

| Документ | Что обновить |
|----------|--------------|
| `docs/architecture.md` | Диаграмма сервисов, поддержка аудио |
| `docs/configuration.md` | WHISPER_URL используется WhisperClient |
| `docs/pipeline/stages.md` | Примеры создания TranscribeStage |
| `docs/adr/006-cloud-model-integration.md` | ProcessingStrategy для Whisper |

---

## Часть 3: Файлы для изменения (итого)

### Код (8 файлов)

| Файл | Тип |
|------|-----|
| `ai_clients/whisper_client.py` | **NEW** |
| `ai_clients/ollama_client.py` | EDIT |
| `ai_clients/__init__.py` | EDIT |
| `services/transcriber.py` | EDIT |
| `services/stages/transcribe_stage.py` | EDIT |
| `pipeline/orchestrator.py` | EDIT |
| `api/routes.py` | EDIT |
| `main.py` | EDIT |

### Документация (8 файлов)

| Файл | Приоритет |
|------|-----------|
| `CLAUDE.md` | HIGH |
| `docs/adr/004-ai-client-abstraction.md` | HIGH |
| `docs/pipeline/02-transcribe.md` | HIGH |
| `docs/api-reference.md` | HIGH |
| `docs/architecture.md` | MEDIUM |
| `docs/configuration.md` | MEDIUM |
| `docs/pipeline/stages.md` | MEDIUM |
| `docs/adr/006-cloud-model-integration.md` | MEDIUM |

---

## Верификация

1. **Синтаксис:** `python3 -m py_compile` для всех изменённых файлов

2. **Аудиофайлы в Inbox:**
   - Положить `.mp3` в inbox
   - Проверить отображение в UI

3. **Транскрибация:**
   - Запустить пошаговую обработку
   - Убедиться что шаг 2 работает

4. **Полный pipeline:**
   - Обработать видео полностью
   - Проверить все этапы

5. **Проверка сервисов:**
   - Whisper health check при старте
   - Ollama health check отдельно
