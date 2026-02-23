---
paths:
  - "backend/app/api/**"
  - "backend/app/models/**"
  - "frontend/src/api/**"
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

## REST Endpoints
- Rules CRUD: `GET/POST/PATCH/DELETE /api/rules`
- Rule actions: `POST /api/rules/:id/pause`, `/resume`, `/trigger`
- Quick convert: `POST /api/convert`
- Logs: `GET /api/logs`
- Settings: `GET/PUT /api/settings`
- Health: `GET /health`

## Frontend API Integration
- Типы из `frontend/src/api/types.ts` — единственный источник правды для TypeScript типов
- НЕ fetch/axios напрямую из компонентов — только через API client
