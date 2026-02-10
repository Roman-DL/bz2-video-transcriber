# Аудит документации docs/pipeline/ (v0.19)

## Цель
Привести документацию в соответствие с кодом после рефакторинга (Фазы 0-5) и требованиями DOCUMENTATION_GUIDELINES.md.

## Принципы (из DOCUMENTATION_GUIDELINES.md)
- **НЕ дублировать**: сигнатуры методов, константы, листинги кода
- **Документировать**: архитектуру, интеграцию, "почему"
- **Код — источник истины**: docstrings в коде всегда актуальны

---

## Вердикты по файлам

| Файл | Вердикт | Объём |
|------|---------|-------|
| **08-orchestrator.md** | Требует существенного обновления | Большой |
| **stages.md** | Требует обновления | Средний |
| **09-api.md** | Требует обновления | Небольшой |
| error-handling.md | Требует минимального обновления | Мелкий |
| 02-transcribe.md | Требует минимального обновления | Мелкий |
| 03-clean.md | Требует минимального обновления | Мелкий |
| README.md | Требует минимального обновления | Мелкий |
| 01-parse.md | ✅ Актуален | — |
| 04-chunk.md | ✅ Актуален | — |
| 05-longread.md | ✅ Актуален | — |
| 06-summarize.md | ✅ Актуален | — |
| 07-save.md | ✅ Актуален | — |

---

## Задача 1: 08-orchestrator.md (приоритет 1)

### Проблемы
1. **Несуществующий класс**: `ProgressEstimator` → актуально `ProgressManager`
2. **Несуществующий файл**: `progress_estimator.py` → актуально `progress_manager.py`
3. **Отсутствует**: описание декомпозиции pipeline/ (v0.15)
4. **Отсутствует**: ProcessingStrategy (v0.19)
5. **Отсутствует**: упоминание StageResultCache (v0.18)
6. **Нарушение guidelines**: таблицы с сигнатурами методов (секция "API методов")
7. **Устаревшие веса**: таблица весов не соответствует STAGE_WEIGHTS в progress_manager.py

### Изменения
- [ ] Переименовать секцию "ProgressEstimator" → "ProgressManager"
- [ ] Обновить путь файла: `progress_estimator.py` → `pipeline/progress_manager.py`
- [ ] Удалить секцию "API методов" с таблицами сигнатур → заменить на "См. docstrings в orchestrator.py"
- [ ] Обновить таблицу весов прогресса по коду (TRANSCRIBING: 45%, CHUNKING: 12%, LONGREAD: 18%)
- [ ] Добавить секцию "Декомпозиция pipeline (v0.15+)" с описанием модулей:
  - orchestrator.py — координация этапов
  - progress_manager.py — веса и расчёт прогресса
  - fallback_factory.py — создание fallback объектов
  - config_resolver.py — override моделей для пошагового режима
  - stage_cache.py — версионирование результатов (v0.18)
  - processing_strategy.py — выбор local/cloud провайдера (v0.19)
- [ ] Добавить ссылки на ADR-002, ADR-005, ADR-006

---

## Задача 2: stages.md (приоритет 2)

### Проблемы
1. **Устаревший импорт**: `from app.services.ai_client import AIClient` → `from app.services.ai_clients import OllamaClient, ClaudeClient`
2. **Нарушение guidelines**: секция "API Reference" с таблицами методов
3. **Пример TelegramSummaryStage**: использует устаревший AIClient

### Изменения
- [ ] Обновить импорт в примере StageRegistry: `AIClient` → использовать ai_clients
- [ ] Удалить секцию "API Reference" → заменить на "API описан в docstrings: `backend/app/services/stages/base.py`"
- [ ] Обновить пример TelegramSummaryStage:
  - Импорт: `from app.services.ai_clients import OllamaClient` или `from app.services.pipeline import ProcessingStrategy`
  - Добавить примечание про выбор провайдера через ProcessingStrategy
- [ ] Добавить ссылку на ADR-004 (AI clients abstraction)

---

## Задача 3: 09-api.md (приоритет 3)

### Проблемы
1. **Отсутствуют**: Cache API endpoints (`/api/cache/*`) из v0.18
2. **Неверная ссылка**: `07-orchestrator.md` → `08-orchestrator.md`
3. **Схема архитектуры**: не включает cache_routes.py

### Изменения
- [ ] Добавить секцию "Cache API" после "Step-by-Step":
  ```
  | GET | `/api/cache/{video_id}` | Информация о кэше |
  | POST | `/api/cache/rerun` | Перезапуск этапа |
  | POST | `/api/cache/version` | Установка текущей версии |
  ```
- [ ] Исправить ссылку на orchestrator: `07-orchestrator.md` → `08-orchestrator.md`
- [ ] Добавить `cache_routes.py` в схему архитектуры и таблицу файлов
- [ ] Добавить ссылку на ADR-005 (Stage Result Cache)

---

## Задача 4: error-handling.md (приоритет 4)

### Проблемы
1. **Устаревший путь**: `backend/app/services/ai_client.py` → удалён в v0.17
2. **Устаревший код**: пример `_extract_json()` вынесен в `app/utils/json_utils.py`

### Изменения
- [ ] Обновить путь: `ai_client.py` → `ai_clients/`
- [ ] Обновить пример: `_extract_json()` → `from app.utils import extract_json`
- [ ] Добавить упоминание `StageError` из stages/base.py

---

## Задача 5: 02-transcribe.md (приоритет 5)

### Проблемы
1. **Устаревшая ссылка**: `ai_client.py` → `ai_clients/ollama_client.py`

### Изменения
- [ ] Обновить "Связанные файлы": `ai_client.py` → `ai_clients/ollama_client.py`
- [ ] В архитектуре: "AIClient (httpx)" → "OllamaClient"

---

## Задача 6: 03-clean.md (приоритет 6)

### Изменения
- [ ] Обновить путь: "AI клиент: backend/app/services/ai_client.py" → `ai_clients/`

---

## Задача 7: README.md (приоритет 7)

### Изменения
- [ ] Добавить ссылку на stages.md в секцию "Оркестрация"
- [ ] Добавить ссылки на ADR-004, ADR-005, ADR-006 в "Связанные документы"

---

## Новые документы

**НЕ создавать** отдельные документы для:
- AI Clients — описано в ADR-004, ADR-006
- Stage Result Cache — описано в ADR-005
- ProcessingStrategy — описано в ADR-006

Достаточно добавить ссылки из существующих документов.

---

## Порядок выполнения

1. **08-orchestrator.md** — центральный документ, сильно устарел
2. **stages.md** — ключевой для Stage abstraction
3. **09-api.md** — добавить Cache API
4. **error-handling.md** — мелкие правки
5. **02-transcribe.md** — одна ссылка
6. **03-clean.md** — одна ссылка
7. **README.md** — добавить ссылки

---

## Верификация

После внесения изменений:
1. Проверить все внутренние ссылки между документами
2. Убедиться что нет дублирования сигнатур методов (grep по `def .*:` в .md файлах)
3. Проверить что импорты в примерах соответствуют актуальному коду
4. Проверить ссылки на файлы в backend/ существуют
