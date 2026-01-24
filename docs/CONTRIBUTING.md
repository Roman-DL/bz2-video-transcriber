---
doc_type: how-to
status: active
updated: 2026-01-24
audience: [developer]
tags:
  - documentation
  - guidelines
---

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
# Backend (порт 8801)
cd backend && source .venv/bin/activate
python -m uvicorn app.main:app --reload --port 8801

# Frontend (порт 5173)
cd frontend && npm run dev
```

### Тестирование

```bash
# Проверка синтаксиса Python
python3 -m py_compile backend/app/api/step_routes.py

# Встроенные тесты модулей
cd backend && source .venv/bin/activate
python -m app.services.parser          # Тесты парсера
python -m app.services.saver            # Тесты saver
python -m app.utils.h2_chunker          # Тесты H2 chunker

# Изолированные тесты (без .env)
python3 -c "
from app.services.parser import parse_dated_offsite_filename
result = parse_dated_offsite_filename('2026.01 Event. # Title (Name).mp3')
print('OK' if result else 'FAIL')
"
```

Подробнее: [testing.md](testing.md)

---

## Планирование новых функций

### Для небольших изменений

- Описать в issue или в начале PR
- После реализации: обновить [overview.md](overview.md) если меняется scope системы

### Для крупных функций

1. Создать RFC-документ в `docs/proposals/{название}.md`
2. Описать: цель, подход, затрагиваемые компоненты
3. После реализации: создать ADR в `docs/adr/`
4. Перенести описание в [overview.md](overview.md), RFC остаётся как история

---

## Architecture Decision Records (ADR)

При принятии значимых архитектурных решений создавать ADR:

```
docs/adr/
├── 001-stage-abstraction.md
├── 002-pipeline-decomposition.md
...
└── 013-api-camelcase-serialization.md
```

**Когда создавать ADR:**
- Новая абстракция или паттерн
- Выбор между несколькими подходами
- Интеграция внешних сервисов
- Изменение архитектуры pipeline

**Формат ADR:**
```markdown
# ADR-XXX: Название решения

## Статус
Принято / Заменено / Отклонено

## Контекст
Описание проблемы или потребности

## Решение
Выбранный подход

## Последствия
Плюсы и минусы решения
```

---

## Чеклисты по типам изменений

### Новый этап pipeline

При добавлении нового этапа обработки:

- [ ] Создать stage в `backend/app/services/stages/{название}_stage.py`
- [ ] Создать сервис в `backend/app/services/{название}.py` (если нужна бизнес-логика)
- [ ] Добавить модель в `backend/app/models/schemas.py`
- [ ] Зарегистрировать stage в `backend/app/services/stages/__init__.py`
- [ ] Создать документацию `docs/pipeline/XX-{название}.md`
- [ ] Обновить `docs/pipeline/README.md` (схема, таблица этапов)
- [ ] Обновить `docs/pipeline/stages.md` (stage абстракция)
- [ ] Обновить `docs/data-formats.md` если новый формат данных
- [ ] Добавить API endpoint в `backend/app/api/step_routes.py` если нужен пошаговый режим

### Новый API endpoint

- [ ] Добавить route в `backend/app/api/`
- [ ] Обновить `docs/architecture.md` (таблица API Endpoints)
- [ ] Обновить `docs/api-reference.md`
- [ ] Обновить `docs/pipeline/09-api.md` если endpoint связан с pipeline

### Изменение конфигурации

- [ ] Добавить поле в `backend/app/config.py` (класс Settings)
- [ ] Обновить `docs/configuration.md` (главный документ!)
- [ ] Обновить `docker-compose.yml` если нужно явное значение
- [ ] Обновить `.env.example`
- [ ] Обновить `CLAUDE.md` если критично для AI-ассистента

### Изменение Web UI

- [ ] Обновить `docs/web-ui.md` (компоненты, режимы)
- [ ] Обновить скриншоты/mockups если существенные визуальные изменения

### Новый промпт или изменение существующего

- [ ] Обновить/создать файл в `config/prompts/{stage}/`
- [ ] Протестировать в пошаговом режиме Web UI
- [ ] Обновить `docs/pipeline/{этап}.md` если меняется логика
- [ ] Обновить `docs/configuration.md` секция "Структура промптов"

### Изменение глоссария

- [ ] Обновить `config/glossary.yaml`
- [ ] Обновить `docs/reference/terminology.md` если добавляются новые категории

---

## Принципы документирования

> Полные гайдлайны: [DOCUMENTATION_GUIDELINES.md](DOCUMENTATION_GUIDELINES.md)

### Что документировать

| Категория | Где | Пример |
|-----------|-----|--------|
| Архитектура | docs/*.md | Схемы, потоки данных |
| Решения | docs/adr/*.md | Почему выбран подход A, а не B |
| API контракты | docs/api-reference.md | HTTP API endpoints |
| Pipeline этапы | docs/pipeline/*.md | Логика, модели данных |
| Конфигурация | docs/configuration.md | Переменные окружения, модели |

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
| Новый сервис/этап | Да | docs/pipeline/, stages.md |
| Рефакторинг метода | Нет | Только docstring в коде |
| Изменение публичного API | Да | architecture.md, api-reference.md |
| Новая конфигурация | Да | configuration.md, CLAUDE.md |
| Архитектурное решение | Да | Создать ADR |
| Новый формат данных | Да | data-formats.md |

---

## Структура документации

```
docs/
├── README.md                    # Навигация
├── overview.md                  # Обзор системы (для всех)
├── architecture.md              # Техническая архитектура
├── configuration.md             # Конфигурация моделей, промптов
├── web-ui.md                    # Web интерфейс
├── CONTRIBUTING.md              # Этот документ
├── DOCUMENTATION_GUIDELINES.md  # Стиль документирования
│
├── api-reference.md             # HTTP API endpoints
├── data-formats.md              # Форматы данных, метрики
├── logging.md                   # Система логирования
├── testing.md                   # Тестирование
├── model-testing.md             # Тестирование моделей
├── deployment.md                # Развёртывание
│
├── pipeline/                    # Этапы обработки
│   ├── README.md
│   ├── stages.md                # Stage абстракция
│   ├── 01-parse.md ... 09-api.md
│   └── error-handling.md
│
├── adr/                         # Architecture Decision Records
│   └── 001-...md ... 013-...md
│
├── reference/
│   ├── terminology.md           # Глоссарий
│   └── progress-calibration.md  # Калибровка прогресса
│
├── proposals/                   # RFC для новых функций
├── research/                    # Исследования
└── archive/                     # Исторические документы
```
