# Процесс разработки

Гайд по добавлению новых функций и поддержанию документации в актуальном состоянии.

## Локальная разработка

### Setup окружения

```bash
# Backend
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Frontend
cd frontend
npm install
```

### Запуск локально

```bash
# Backend
cd backend && source .venv/bin/activate
uvicorn app.main:app --reload

# Frontend
cd frontend && npm run dev
```

### Тестирование

```bash
# Проверка синтаксиса Python
python3 -m py_compile backend/app/api/routes.py

# Unit tests
cd backend && source .venv/bin/activate
pytest tests/
```

Подробнее: [testing.md](testing.md)

---

## Чеклисты по типам изменений

### Новый API endpoint

- [ ] Добавить route в `backend/app/api/`
- [ ] Pydantic модель (`CamelCaseModel`) в `backend/app/models/`
- [ ] Обновить `docs/api-reference.md`
- [ ] Обновить `docs/ARCHITECTURE.md` если меняется архитектура

### Изменение Converter

- [ ] Поддержать оба направления: MD→GDoc и GDoc→MD
- [ ] Обновить `docs/architecture/01-converter.md`
- [ ] Проверить маппинг каллаутов (8 типов)
- [ ] Тесты на реальных документах

### Изменение Rules Engine / Sync Manager

- [ ] Проверить все 3 режима (`once`, `one-way`, `two-way`)
- [ ] Обновить SQL схему если нужно (миграция!)
- [ ] Обновить `docs/architecture/02-rules-engine.md`
- [ ] Проверить change detection логику

### Изменение Google Drive Client

- [ ] Проверить rate limits (max 3 concurrent)
- [ ] Retry strategy для 429/500/503
- [ ] Обновить `docs/architecture/03-google-drive.md`

### Изменение конфигурации

- [ ] Обновить `docs/configuration.md`
- [ ] Обновить `docker-compose.yml` если нужно
- [ ] Обновить `.env.example`
- [ ] Обновить `CLAUDE.md` если критично

### Изменение Web UI

- [ ] Tailwind CSS, НЕ inline styles
- [ ] API вызовы через client, НЕ fetch/axios напрямую
- [ ] Типы из `frontend/src/api/types.ts`
- [ ] Для нового экрана — навык `/frontend-design`

---

## Architecture Decision Records (ADR)

При принятии значимых архитектурных решений создавать ADR:

**Когда создавать:**
- Выбор между несколькими подходами
- Новая абстракция или паттерн
- Интеграция внешних сервисов

**Формат:**
```markdown
# ADR-NNN: Название решения

## Статус
Принято / Заменено / Отклонено

## Контекст
Описание проблемы

## Решение
Выбранный подход

## Альтернативы
Что рассматривалось

## Последствия
Плюсы и минусы
```

---

## Принципы документирования

> Полные гайдлайны: [DOCUMENTATION_GUIDELINES.md](DOCUMENTATION_GUIDELINES.md)

### Что документировать

| Категория | Где | Пример |
|-----------|-----|--------|
| Архитектура | docs/*.md | Схемы, потоки данных |
| Решения | docs/decisions/*.md | Почему polling, а не inotify |
| API контракты | docs/api-reference.md | HTTP API endpoints |
| Модули | docs/architecture/*.md | Converter, Rules Engine, Google Drive |
| Конфигурация | docs/configuration.md | Переменные окружения |

### Что НЕ документировать

- Сигнатуры методов (читаются из кода)
- Константы и переменные (читаются из кода)
- Примеры кода с конкретными значениями (устаревают)

### Принцип: код — источник истины

- Docstrings в коде всегда актуальны
- Документация описывает "что" и "почему", не "как"
- Обновлять документы сразу после реализации

---

## Когда обновлять документацию

| Изменение | Обновить docs? | Что обновить |
|-----------|----------------|--------------|
| Новый сервис/модуль | Да | architecture/, ARCHITECTURE.md |
| Рефакторинг метода | Нет | Только docstring в коде |
| Изменение API | Да | api-reference.md |
| Новая конфигурация | Да | configuration.md, CLAUDE.md |
| Архитектурное решение | Да | Создать ADR |

---

_Связанные документы: [WORKFLOW.md](WORKFLOW.md) | [DOCUMENTATION_GUIDELINES.md](DOCUMENTATION_GUIDELINES.md) | [COMMANDS-REFERENCE.md](COMMANDS-REFERENCE.md)_
