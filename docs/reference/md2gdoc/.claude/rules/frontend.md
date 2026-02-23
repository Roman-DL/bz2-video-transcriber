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

## Процесс разработки UI

**ВСЕГДА при создании нового экрана или значительной переработке UI — используй навык `/frontend-design`.**

Навык объединяет дизайн и реализацию:
1. Design thinking → визуальный макет в Pencil (pencil.dev)
2. Показать скриншот → итерации с пользователем
3. Утвердили → генерация React + Tailwind кода по макету

**Когда НЕ нужен навык:** мелкие правки (поменять текст, цвет, добавить кнопку в существующий UI) — реализуй напрямую.

> См. ADR-001 для обоснования подхода.

## Компоненты
- Rules Management: CRUD для правил, таблица со статусами
- Conversion Logs: фильтрация, поиск по логам конвертации
- Settings: Google API connection test, polling interval
- Dashboard: overview активных правил и последних конвертаций
