---
paths:
  - "frontend/src/**"
---

# Rules: Frontend

## Стек
- React + Vite + Tailwind CSS
- TypeScript

## Стилизация
- Tailwind CSS — НЕ использовать inline styles или CSS modules
- Utility-first подход

## API интеграция
- Типы из `frontend/src/api/types.ts` — единственный источник правды для TypeScript типов
- НЕ делать fetch/axios напрямую из компонентов — только через API client (`frontend/src/api/client.ts`)

## Компоненты
- Rules Management: CRUD для правил, таблица со статусами
- Conversion Logs: фильтрация, поиск по логам конвертации
- Settings: Google API connection test, polling interval
- Dashboard: overview активных правил и последних конвертаций
