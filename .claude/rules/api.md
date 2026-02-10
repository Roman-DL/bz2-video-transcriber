---
globs: backend/app/api/**,backend/app/models/schemas.py,frontend/src/api/**
---

# Rules: API & Models

## CamelCaseModel
- ВСЕГДА наследовать response-модели от `CamelCaseModel`:
  ```python
  class MyResponse(CamelCaseModel):
      some_field: str  # → JSON: "someField"
  ```
- Python код: `snake_case` | API JSON: `camelCase` | TypeScript: `camelCase`
- ВСЕГДА возвращать Pydantic модели из endpoints, НЕ `dict`
- `populate_by_name=True` — принимает оба формата на входе

## TokensUsed
- ВСЕГДА включать `TokensUsed` в модели результатов LLM-шагов
- Поля: `input`, `output`, `total` (computed)

## Step API Pattern
- Endpoints: `/api/step/{stage}` (clean, longread, summarize, story, slides)
- Поддержка `model` и `prompt_overrides` (опционально)
- Промпт-оверрайды: `{"system": "system_v2", "user": "user"}`

## Prompts API
- `GET /api/prompts/{stage}` — список вариантов промптов для этапа
- UI показывает селекторы промптов в пошаговом режиме (step-by-step)

## Cache API
- `GET /api/cache/{video_id}` — информация о кэше
- `POST /api/cache/rerun` — перезапуск этапа
- `POST /api/cache/version` — установка текущей версии

## Frontend Utils
- ВСЕГДА использовать `formatUtils`: `formatTime()`, `formatCost()`, `formatTokens()`
- НЕ форматировать метрики вручную в компонентах
