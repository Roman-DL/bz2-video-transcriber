---
globs: frontend/src/components/**,frontend/src/utils/**,frontend/src/hooks/**,frontend/src/contexts/**
---

# Rules: Frontend

## Форматирование
- ВСЕГДА использовать `formatUtils` для метрик: `formatTime()`, `formatCost()`, `formatTokens()`
- НЕ форматировать числа и метрики вручную в компонентах

## API интеграция
- Типы из `frontend/src/api/types.ts` — единственный источник правды для TypeScript типов
- API хуки в `frontend/src/api/hooks/` — использовать готовые (`useInbox`, `useServices`, `usePrompts`, `useModels`, `useArchive`, `useSteps`)
- НЕ делать fetch/axios напрямую из компонентов — только через `frontend/src/api/client.ts`

## Стилизация
- Tailwind CSS — НЕ использовать inline styles или CSS modules

## Настройки
- `SettingsContext` (`frontend/src/contexts/SettingsContext.tsx`) — единственный способ доступа к настройкам
- НЕ пробрасывать settings через props если есть контекст

## Документация
- Описание UI: `docs/web-ui.md`
