---
name: frontend-design
description: Проектирование и реализация production-grade интерфейсов. Сначала создаёт визуальный макет в Pencil для обсуждения, затем реализует утверждённый дизайн в React + Tailwind код.
---

Этот навык создаёт distinctive, production-grade интерфейсы в два этапа: сначала визуальный дизайн в Pencil (для обсуждения и итераций), затем реализация в код по утверждённому макету.

Пользователь описывает что нужно: компонент, страницу, экран или приложение. Может указать контекст, аудиторию, технические ограничения.

## Пре-реквизиты

**Pencil MCP-сервер должен быть подключён.** Проверь доступность инструментов `mcp__pencil__*` (например, `mcp__pencil__get_editor_state`). Если недоступны — сообщи пользователю: нужно установить расширение Pencil в VSCode и открыть `.pen` файл. Подробности в `docs/configuration.md` (секция "Pencil").

## Этап 1: Дизайн в Pencil

### Design Thinking

Перед созданием макета — определи концепцию:
- **Purpose**: Какую задачу решает интерфейс? Кто пользователь?
- **Tone**: Выбери BOLD направление: brutally minimal, maximalist, retro-futuristic, organic/natural, luxury/refined, playful, editorial/magazine, brutalist/raw, art deco, soft/pastel, industrial/utilitarian. Используй как вдохновение, но создай уникальный дизайн.
- **Constraints**: Технические требования (фреймворк, перформанс, accessibility).
- **Differentiation**: Что делает этот интерфейс ЗАПОМИНАЮЩИМСЯ?

**CRITICAL**: Выбери ясное концептуальное направление и выполни его точно. Bold максимализм и refined минимализм оба работают — ключ в intentionality, не intensity.

### Создание макета

Используй MCP-инструменты Pencil для создания визуального прототипа:

1. **Открой или создай .pen файл** — `open_document` в `frontend/designs/` (например, `frontend/designs/dashboard.pen`)
2. **Получи style guide** — `get_style_guide_tags` → `get_style_guide(tags)` для визуального вдохновения
3. **Получи guidelines** — `get_guidelines(topic)` для правил работы с .pen
4. **Создай макет** — `batch_design` для построения layout, компонентов, типографики
5. **Сделай скриншот** — `get_screenshot` и покажи пользователю
6. **Итерируй** — по фидбеку пользователя меняй стили, layout, элементы прямо в Pencil

**Директория макетов:** `frontend/designs/` — все `.pen` файлы сохраняются здесь. Именование: `{экран}.pen` (например, `dashboard.pen`, `settings.pen`, `rule-editor.pen`).

### Aesthetic Guidelines (для Pencil макета)

- **Typography**: Выбирай distinctive, characterful шрифты. Избегай generic (Arial, Inter, Roboto, system fonts). Пара: выразительный display font + refined body font.
- **Color & Theme**: Cohesive aesthetic. Dominant colors с sharp accents побеждают робкие равномерные палитры. Используй CSS variables через `set_variables`.
- **Spatial Composition**: Unexpected layouts. Asymmetry. Overlap. Diagonal flow. Grid-breaking. Generous negative space ИЛИ controlled density.
- **Visual Details**: Atmosphere и depth вместо solid colors. Градиенты, текстуры, геометрические паттерны, тени, декоративные границы.

### Anti-patterns (чего НИКОГДА не делать)

- Generic AI-aesthetics: Inter + purple gradient на белом фоне
- Predictable cookie-cutter layouts без характера
- Одинаковый стиль в разных проектах — каждый дизайн уникален
- Конвергенция на "безопасных" выборах (Space Grotesk, синий + белый)

### Итерации с пользователем

После показа скриншота — жди фидбек. Пользователь может попросить:
- Поменять цветовую схему или акценты
- Изменить layout или расположение элементов
- Попробовать другой стиль типографики
- Добавить/убрать элементы
- Сравнить несколько вариантов (скопировать экран, сделать вариацию)

Каждая итерация в Pencil — секунды, не минуты. Продолжай до подтверждения: "утверждаю" / "ок, делай код" / аналог.

## Этап 2: Реализация в код

**Только после утверждения макета пользователем.**

### Анализ макета перед кодом

Считай из Pencil точные параметры:
- `batch_get` — структура, свойства компонентов, цвета, размеры
- `get_variables` — CSS variables и темы
- `get_screenshot` — для финальной сверки

### Генерация кода

React + TypeScript + Tailwind код, который:

**Визуально идентичен макету:**
- Точные цвета, размеры, отступы из макета
- Та же типографика и иерархия
- Тот же layout (flex/grid)

**Production-grade:**
- Proper TypeScript типизация
- React hooks и state management
- API интеграция через client (НЕ fetch/axios напрямую)
- Error и loading состояния
- Keyboard navigation и accessibility basics

**С motion и polish:**
- CSS transitions для hover/focus states
- Staggered animations для списков (animation-delay)
- Micro-interactions где уместно
- Smooth loading states (skeleton, shimmer)

### Сверка

После генерации кода — сверь с макетом визуально. Если есть расхождения — исправь.

## Режим без Pencil (мелкие правки)

Для простых доработок существующего UI (поменять текст, цвет, добавить кнопку) — реализуй напрямую, сохраняя стиль существующих компонентов. Pencil макет не нужен.

**IMPORTANT**: Match implementation complexity to the aesthetic vision. Maximalist designs → elaborate code с animations и effects. Minimalist designs → restraint, precision, careful spacing и subtle details.
