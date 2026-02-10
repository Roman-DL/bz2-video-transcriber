# План: Завершение миграции API на camelCase (v0.59)

## Архитектурное решение

**Выбран подход: camelCase для API контракта**

| Слой | Формат | Пример |
|------|--------|--------|
| Python код (внутри) | snake_case | `raw_transcript` |
| API JSON (контракт) | camelCase | `rawTranscript` |
| TypeScript (frontend) | camelCase | `rawTranscript` |

**Правила:**
1. Все API endpoints возвращают **Pydantic модели**, не `dict`
2. Все response/request модели наследуют от **CamelCaseModel**
3. `populate_by_name=True` позволяет принимать оба формата на входе

---

## Endpoints для миграции

| Endpoint | Текущий return | После миграции |
|----------|---------------|----------------|
| `/api/models/available` | `dict` ❌ | `AvailableModelsResponse` |
| `/api/models/default` | `dict` ❌ | `DefaultModelsResponse` |
| `/api/models/config` | `dict` ❌ | Оставить dict (сырой YAML) |
| `/api/archive` | `dict` ❌ | `ArchiveResponse` |
| `/api/archive/results` | `dict` ❌ | `PipelineResultsResponse` |
| `/api/cache/.../rerun` | `dict` ❌ | `CacheRerunResponse` |
| `/api/cache/.../version` | `dict` ❌ | `CacheVersionResponse` |

---

# ФАЗА 1: Backend Models (schemas.py) ✅ ВЫПОЛНЕНО

**Цель:** Добавить response модели для всех API endpoints.

**Файл:** `backend/app/models/schemas.py` (строки 1226-1323)

**Добавлены модели:**

| Модель | Назначение |
|--------|------------|
| `WhisperModelConfig` | Конфигурация Whisper модели |
| `ModelPricing` | Цены за 1M токенов |
| `ClaudeModelConfig` | Конфигурация Claude модели |
| `ProviderStatus` | Статус провайдера |
| `ProvidersInfo` | Информация о провайдерах |
| `AvailableModelsResponse` | GET /api/models/available |
| `DefaultModelsResponse` | GET /api/models/default |
| `ArchiveItem` | Элемент архива |
| `ArchiveResponse` | GET /api/archive |
| `PipelineResultsResponse` | GET /api/archive/results |
| `CacheVersionResponse` | POST /api/cache/version |

**Примечание:** `CacheRerunResponse` не добавлен — `RerunResponse` уже существует в `cache.py:284`.

**Проверка:** `python3 -m py_compile app/models/schemas.py` ✅

---

# ФАЗА 2: Backend Routes (API endpoints) ✅ ВЫПОЛНЕНО

**Цель:** Заменить `-> dict` на типизированные response модели.

## 2.1 models_routes.py ✅

**Файл:** `backend/app/api/models_routes.py`

**Изменения:**
- `get_available_models()` → `AvailableModelsResponse`
- `get_default_models()` → `DefaultModelsResponse`
- Добавлены импорты: `AvailableModelsResponse`, `DefaultModelsResponse`, `WhisperModelConfig`, `ClaudeModelConfig`, `ProvidersInfo`, `ProviderStatus`

## 2.2 routes.py ✅

**Файл:** `backend/app/api/routes.py`

**Изменения:**
- `list_archive()` → `ArchiveResponse` (использует `ArchiveItem`)
- `get_archive_results()` → `PipelineResultsResponse` (валидация через `PipelineResults.model_validate()`)
- Добавлены импорты: `ArchiveItem`, `ArchiveResponse`, `PipelineResults`, `PipelineResultsResponse`

## 2.3 cache_routes.py ✅

**Файл:** `backend/app/api/cache_routes.py`

**Изменения:**
- `set_current_version()` → `CacheVersionResponse`
- Добавлен импорт: `CacheVersionResponse`
- **Примечание:** `/rerun` уже использует `RerunResponse` из `cache.py`

**Проверка фазы 2:** ✅ Все файлы прошли `py_compile`

```bash
# После деплоя:
curl -s http://100.64.0.1:8801/api/models/available | jq 'keys'
# Ожидается: ["claudeModels", "ollamaModels", "providers", "whisperModels"]

curl -s http://100.64.0.1:8801/api/archive | jq '.tree | to_entries[0].value | to_entries[0].value[0] | keys'
# Ожидается: ["eventType", "midFolder", "speaker", "title"]
```

---

# ФАЗА 3: Документация

**Цель:** Задокументировать архитектурное решение и обновить существующую документацию.

## 3.1 Новый ADR: docs/adr/013-api-camelcase-serialization.md

**Структура:**
```markdown
# ADR-013: CamelCase сериализация для API

## Статус
Принято (v0.59)

## Контекст
- Python использует snake_case (PEP 8)
- TypeScript/JavaScript использует camelCase
- v0.58 начал миграцию, но не все endpoints были обновлены

## Решение
1. Все API endpoints возвращают Pydantic модели (не dict)
2. Все модели наследуют от CamelCaseModel
3. Python код внутри использует snake_case
4. API JSON использует camelCase

## Последствия
- [+] Явные типизированные контракты API
- [+] Автодокументация через OpenAPI
- [+] Стандартный подход для REST API
- [-] Все endpoints должны использовать Pydantic модели
```

## 3.2 Обновить: docs/api-reference.md

**Добавить секцию:**
```markdown
## Внутренний API (Backend)

### Соглашения

- Все ответы API в **camelCase**
- Запросы принимают и camelCase и snake_case (совместимость)

### Endpoints

| Endpoint | Метод | Response Model |
|----------|-------|----------------|
| `/api/models/available` | GET | `AvailableModelsResponse` |
| `/api/models/default` | GET | `DefaultModelsResponse` |
| `/api/archive` | GET | `ArchiveResponse` |
| `/api/archive/results` | GET | `PipelineResultsResponse` |
| ... | | |
```

## 3.3 Обновить: docs/data-formats.md

**Добавить секцию про JSON сериализацию:**
```markdown
## JSON API формат (v0.59+)

Все JSON ответы API используют **camelCase** для ключей.

| Python модель | JSON ключ |
|---------------|-----------|
| `raw_transcript` | `rawTranscript` |
| `cleaned_length` | `cleanedLength` |
| `processing_time_sec` | `processingTimeSec` |
```

## 3.4 Обновить: CLAUDE.md

**Добавить/обновить секцию:**
```markdown
## API Serialization Rules (v0.59+)

**Правило:** Все API endpoints должны возвращать Pydantic модели, не `dict`.

| Слой | Формат |
|------|--------|
| Python код | snake_case |
| API JSON | camelCase |
| TypeScript | camelCase |

**Как добавить новый endpoint:**
1. Создать response модель наследующую от `CamelCaseModel`
2. Указать return type: `async def my_endpoint() -> MyResponse:`
3. Использовать `response_model=` в декораторе (опционально)

Подробнее: [docs/adr/013-api-camelcase-serialization.md](docs/adr/013-api-camelcase-serialization.md)
```

**Проверка фазы 3:**
- Документы созданы/обновлены
- Ссылки корректны

---

# Сводка по фазам

| Фаза | Описание | Файлы | Статус |
|------|----------|-------|--------|
| **1** | Backend Models | `schemas.py` | ✅ Выполнено |
| **2** | Backend Routes | `models_routes.py`, `routes.py`, `cache_routes.py` | ✅ Выполнено |
| **3** | Документация | `adr/013-*.md`, `api-reference.md`, `data-formats.md`, `CLAUDE.md` | ⏳ Следующая |

---

# Версионирование

После завершения всех фаз: обновить `frontend/package.json` до `v0.59.0`
