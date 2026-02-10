# Исследование: Выбор фронтенд-стека для Админ-портала БЗ 2.0

> Дата: 2026-02-08
> Контекст: Админ-портал БЗ 2.0 ([docs/reference/admin-portal.md](../../reference/admin-portal.md))
> Статус: Решение принято

---

## Executive Summary

Для админ-портала БЗ 2.0 выбран стек **React + Refine + Tailwind CSS + TypeScript + Vite**. Решение основано на анализе требований портала, сравнении с текущим стеком bz2-video-transcribe и оценке трёх фреймворков для админ-панелей.

| Критерий | Решение |
|----------|---------|
| UI-фреймворк | React (опыт из bz2-video-transcribe) |
| Admin-фреймворк | Refine (headless, Tailwind-совместим, RBAC бесплатно) |
| Стилизация | Tailwind CSS (опыт из bz2-video-transcribe) |
| Сборка | Vite (опыт из bz2-video-transcribe) |
| Типизация | TypeScript |
| Data fetching | React Query (встроен в Refine) |

---

## 1. Требования портала (из admin-portal.md)

Ключевые UI-паттерны, определившие выбор:

| Паттерн | Где используется | Сложность |
|---------|-----------------|-----------|
| Таблицы с фильтрами и пагинацией | Материалы, пользователи, логи | Высокая |
| CRUD-формы | Материалы, настройки | Средняя |
| Дашборды с графиками | Аналитика поиска, пользователей, LLM-стоимость | Высокая |
| Bulk-операции | Модерация пользователей | Средняя |
| Авторизация + RBAC | Telegram Login Widget, роли admin/tab_team | Средняя |
| Многостраничная навигация | 6+ экранов с боковым меню | Средняя |

**Вывод:** это полноценная админ-панель, не одностраничный dashboard. Нужны роутинг, авторизация, таблицы, формы, графики.

---

## 2. Почему не голый React (как в bz2-video-transcribe)

В bz2-video-transcribe используется минималистичный стек: React + Vite + Tailwind + 7 runtime-зависимостей. Это работает, потому что bz2 — **одностраничное приложение** без роутинга, авторизации и сложных таблиц.

Для админ-портала голый React потребует писать с нуля:
- Роутинг (react-router)
- Авторизацию (JWT, guards, redirect)
- Таблицы с сортировкой, фильтрами, пагинацией
- CRUD-логику (create/edit/delete формы)
- Data providers (API-слой)

Admin-фреймворк даёт всё это из коробки.

---

## 3. Сравнение вариантов фронтенда

### 3.1 Jinja2 + htmx

| Плюсы | Минусы |
|-------|--------|
| Нет JS-фреймворка | Ограниченная интерактивность |
| Серверный рендеринг | Графики — через JS в любом случае |
| Простые формы нативно | Bulk-операции сложнее |
| Минимум инфраструктуры | Потолок UX ниже |

**Вердикт:** подходит для простых CRUD-админок, но дашборды аналитики с графиками и интерактивными фильтрами требуют JS. Половина портала будет на htmx, половина — на JS. Смешанный подход.

### 3.2 React + react-admin

| Плюсы | Минусы |
|-------|--------|
| Зрелый (с 2016) | Привязан к Material UI |
| Минимум бойлерплейта | RBAC — платный (Enterprise) |
| Готовые CRUD-компоненты | Realtime — платный |
| Большое community | Кастомизация дизайна ограничена |

**Вердикт:** быстрый старт, но результат выглядит как generic Material UI админка. Кастомизировать внешний вид под Tailwind невозможно. RBAC (нужен для admin/tab_team) — платная фича.

### 3.3 React + Refine (выбран)

| Плюсы | Минусы |
|-------|--------|
| Headless — любой UI/CSS | Больше кода на старте |
| Tailwind-совместим | Моложе react-admin (с 2021) |
| RBAC бесплатно (open-source) | Нужно собирать UI самому |
| Realtime бесплатно | |
| REST API data provider | |
| React Query встроен | |
| Роутинг встроен | |

**Вердикт:** оптимальный баланс для соло-разработчика с опытом React + Tailwind. Headless-подход позволяет полный контроль над дизайном дашбордов и кастомных виджетов аналитики.

### Сводная таблица

| Критерий | Jinja2 + htmx | react-admin | **Refine** |
|----------|---------------|-------------|------------|
| Таблицы/фильтры | С нуля | Из коробки | Из коробки (headless) |
| Графики | Сложнее (JS вставки) | + recharts | + recharts |
| Формы | Нативные HTML | Из коробки | Из коробки (headless) |
| Роутинг | Серверный | react-router | Встроен |
| Авторизация | Серверные сессии | Встроена | Встроена |
| RBAC | С нуля | Платный | **Бесплатный** |
| Tailwind | Да | Нет (Material UI) | **Да** |
| Кривая обучения | Низкая | Средняя | Средняя |
| Контроль дизайна | Полный | Ограничен MUI | **Полный** |

---

## 4. Выбранный стек

```
React 19 + TypeScript + Vite + Tailwind CSS 4
         │
         ├── Refine          — CRUD, роутинг, авторизация, data providers
         ├── React Query     — data fetching (встроен в Refine)
         ├── Recharts        — графики для дашбордов аналитики
         ├── Lucide React    — иконки (как в bz2)
         └── react-router    — навигация (интеграция через Refine)
```

### Что переиспользуется из bz2-video-transcribe

| Элемент | Переиспользуется |
|---------|-----------------|
| React + TypeScript | Да, те же версии |
| Vite | Да, та же конфигурация |
| Tailwind CSS | Да, те же утилиты |
| Lucide React | Да, иконки |
| React Query | Да (в bz2 — @tanstack/react-query, в Refine — встроен) |
| Axios | Да (REST data provider) |
| Архитектура компонентов | Частично (composition, hooks) |

### Что новое

| Элемент | Зачем |
|---------|-------|
| Refine | Admin-фреймворк: CRUD, auth, RBAC, data providers |
| react-router | Многостраничная навигация (6+ экранов) |
| Recharts | Графики: динамика использования, стоимость LLM |

---

## 5. Применимость скиллов

### SKILL: frontend-patterns — применим

Скилл содержит React + TypeScript паттерны, напрямую применимые в проекте:

| Паттерн | Применение в портале | Примечание |
|---------|---------------------|------------|
| Composition (Card, CardHeader) | Карточки материалов, виджеты аналитики | Используем с Tailwind |
| Compound Components (Tabs) | Вкладки аналитики: поиск / пользователи / LLM | |
| useDebounce | Поиск и фильтрация в таблицах | |
| Context + Reducer | Состояние авторизации (user, role, permissions) | |
| Controlled Forms | CRUD материалов, настройки системы | |
| Virtualization | Таблица системных логов (тысячи записей) | @tanstack/react-virtual |
| Error Boundary | Production-обязательно | |
| Code Splitting (lazy) | Lazy load дашбордов аналитики (recharts тяжёлый) | |
| Framer Motion | Модалки, переходы между страницами | Опционально |

**Что НЕ использовать из скилла:**
- Самописный useQuery (строки 146-195) — Refine использует React Query из коробки
- Render Props (DataLoader) — устаревший паттерн, React Query заменяет
- Самописный fetch-wrapper — Refine data provider покрывает это

### SKILL: backend-patterns — не применим

Скилл написан для **Node.js / Next.js / TypeScript + Supabase**. Бэкенд портала — **Python / FastAPI / SQLAlchemy**.

| Паттерн | Концептуально полезен | Код применим |
|---------|----------------------|-------------|
| RESTful API Structure | Да | Нет (FastAPI, не Express) |
| Repository Pattern | Нет (SQLAlchemy ORM) | Нет |
| Service Layer | Да (уже есть в проекте) | Нет |
| Middleware (withAuth) | Нет (FastAPI Depends()) | Нет |
| JWT / RBAC | Да | Нет (Python реализация) |
| Error Handling | Нет (FastAPI exception handlers) | Нет |
| Rate Limiting | Да | Нет |
| Redis Caching | Да | Нет |

**Рекомендация:** для бэкенд-паттернов опираться на существующий код bz2-video-transcribe (FastAPI + Pydantic + async services), а не на этот скилл.

---

## 6. Источники

- [React-Admin vs Refine: Feature Comparison (marmelab)](https://marmelab.com/blog/2023/07/04/react-admin-vs-refine.html)
- [Refine vs React-Admin (refine.dev)](https://refine.dev/blog/refine-vs-react-admin/)
- [Refine GitHub](https://github.com/refinedev/refine)
- [npm trends: react-admin vs refine](https://npmtrends.com/react-admin-vs-refine)
