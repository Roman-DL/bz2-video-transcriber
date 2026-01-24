---
doc_type: adr
status: accepted
created: 2025-01-24
updated: 2026-01-24
audience: [developer]
tags:
  - architecture
  - adr
  - api
---

# ADR-013: CamelCase сериализация для API

## Статус

Принято (v0.59)

## Контекст

До v0.58 API endpoints возвращали смешанные форматы данных:
- Часть endpoints возвращала `dict` напрямую (без типизации)
- Часть использовала Pydantic модели с snake_case
- Frontend вынужден был обрабатывать разные форматы

Проблемы:
- Python использует snake_case (PEP 8)
- TypeScript/JavaScript конвенции — camelCase
- Отсутствие единого контракта между backend и frontend
- Отсутствие автодокументации через OpenAPI
- v0.58 начал миграцию с `CamelCaseModel`, но не все endpoints были обновлены

## Решение

### Архитектурное правило

| Слой | Формат | Пример |
|------|--------|--------|
| Python код (внутри) | snake_case | `raw_transcript`, `tokens_used` |
| API JSON (контракт) | camelCase | `rawTranscript`, `tokensUsed` |
| TypeScript (frontend) | camelCase | `rawTranscript`, `tokensUsed` |

### Реализация

1. **Все API endpoints возвращают Pydantic модели**, не `dict`

2. **Все response/request модели наследуют от `CamelCaseModel`:**
   ```python
   from pydantic import BaseModel, ConfigDict
   from pydantic.alias_generators import to_camel

   class CamelCaseModel(BaseModel):
       """Python: snake_case, JSON: camelCase."""
       model_config = ConfigDict(
           alias_generator=to_camel,
           populate_by_name=True,
       )
   ```

3. **`populate_by_name=True`** позволяет принимать оба формата на входе (совместимость)

4. **Явная типизация endpoints:**
   ```python
   @router.get("/models/available")
   async def get_available_models() -> AvailableModelsResponse:
       ...
   ```

### Миграция endpoints (v0.59)

| Endpoint | До миграции | После миграции |
|----------|-------------|----------------|
| `GET /api/models/available` | `dict` | `AvailableModelsResponse` |
| `GET /api/models/default` | `dict` | `DefaultModelsResponse` |
| `GET /api/models/config` | `dict` | Оставлен `dict` (сырой YAML) |
| `GET /api/archive` | `dict` | `ArchiveResponse` |
| `GET /api/archive/results` | `dict` | `PipelineResultsResponse` |
| `POST /api/cache/version` | `dict` | `CacheVersionResponse` |

**Примечание:** `/api/models/config` оставлен как `dict`, так как возвращает сырую структуру YAML без трансформации.

### Добавленные модели (schemas.py)

```python
# Models API
class WhisperModelConfig(CamelCaseModel): ...
class ModelPricing(CamelCaseModel): ...
class ClaudeModelConfig(CamelCaseModel): ...
class ProviderStatus(CamelCaseModel): ...
class ProvidersInfo(CamelCaseModel): ...
class AvailableModelsResponse(CamelCaseModel): ...
class DefaultModelsResponse(CamelCaseModel): ...

# Archive API
class ArchiveItem(CamelCaseModel): ...
class ArchiveResponse(CamelCaseModel): ...
class PipelineResultsResponse(CamelCaseModel): ...

# Cache API
class CacheVersionResponse(CamelCaseModel): ...
```

## Последствия

### Преимущества

- **Явные типизированные контракты API** — каждый endpoint имеет модель
- **Автодокументация через OpenAPI** — Swagger UI показывает структуру response
- **Стандартный подход для REST API** — camelCase для JSON общепринят
- **Упрощённый frontend** — не нужно преобразовывать snake_case → camelCase
- **Валидация на уровне Pydantic** — ошибки ловятся раньше

### Ограничения

- Все endpoints должны использовать Pydantic модели (не `dict`)
- Старые `pipeline_results.json` в snake_case требуют миграции или graceful handling
- Изменение формата требует обновления frontend типов

### Как добавить новый endpoint

1. Создать response модель наследующую от `CamelCaseModel`:
   ```python
   class MyNewResponse(CamelCaseModel):
       some_field: str
       another_field: int
   ```

2. Указать return type в endpoint:
   ```python
   @router.get("/my-endpoint")
   async def my_endpoint() -> MyNewResponse:
       return MyNewResponse(some_field="value", another_field=42)
   ```

3. Опционально добавить `response_model` в декоратор:
   ```python
   @router.get("/my-endpoint", response_model=MyNewResponse)
   ```

## Связанные ADR

- [ADR-009: Extended Metrics](009-extended-metrics.md) — метрики в моделях
- [ADR-012: Statistics Tab](012-statistics-tab.md) — унификация API для статистики
