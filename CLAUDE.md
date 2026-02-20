# bz2-video-transcriber

Система автоматической транскрипции и саммаризации видеозаписей для БЗ 2.0.

## Инструкции для Claude

- **Язык общения:** Русский
- **Язык кода:** Английский (имена переменных, функций, комментарии в коде)
- **Язык документации:** Русский
- **Git commits:** Русский, формат "{тип}: описание" (docs, feat, fix, refactor)
- **Версионирование:** После коммита новых фич — ОБЯЗАТЕЛЬНО предложи обновить версию в `frontend/package.json`

## Документирование кода

При реализации функций следуй [гайдлайнам по документированию](docs/DOCUMENTATION_GUIDELINES.md):
- **Docstrings в коде** — обязательны для публичных методов (Google-style)
- **Внешняя документация** — только архитектура, интеграция, решения
- **Не дублируй код в docs** — ИИ читает код напрямую

## Quick Start

```bash
# Проверить AI сервисы
curl http://100.64.0.1:11434/api/version  # Ollama
curl http://100.64.0.1:9000/health        # Whisper

# Деплой на сервер (локальный docker-compose не работает!)
./scripts/deploy.sh

# Web UI (HTTPS через Traefik)
https://transcriber.home     # Основной доступ
https://transcriber.home/health  # Health check
```

## Архитектура

```
Video + [Slides] → Parse → Whisper → Clean ─┬─→ [Slides] → Longread → Summary → Chunk (H2, ≤600w) + Describe → Save (educational)
                                            └─→ [Slides] → Story → Chunk (H2, ≤600w) + Describe → Save (leadership)
```

> **v0.25+:** Chunk теперь детерминированный (парсинг H2 заголовков), выполняется ПОСЛЕ longread/story.
> **v0.51+:** Опциональный шаг Slides появляется перед Longread/Story если пользователь прикрепил слайды.
> **v0.60+:** Chunk разбивает секции >600 слов по параграфам. BZ2-Bot v1.0 формат.
> **v0.62+:** Description generation перенесена из Save в Chunk. Save — чистое сохранение файлов.

## Ключевые ограничения

<!--
Что AI НЕ должен делать. ОБЯЗАТЕЛЬНО обновлять после каждой проблемы!
Формулировки: "НИКОГДА не...", "ВСЕГДА проверяй..."
-->

1. **docker-compose НЕ работает локально** — пути к данным (`/mnt/main/work/bz2/video`) существуют только на сервере. Единственный способ деплоя: `./scripts/deploy.sh`
2. **Claude — default для всех LLM операций** (v0.29+, ADR-007) — требуется `ANTHROPIC_API_KEY`. Локальные модели через Ollama — для тестирования
3. **НИКОГДА не добавлять fallback между провайдерами** — при ошибках пробрасывать `PipelineError` вызывающему коду
4. **API endpoints — ВСЕГДА Pydantic модели** (`CamelCaseModel`), не `dict` — Python `snake_case` → JSON `camelCase`
5. **Chunk детерминистический** — парсинг H2 заголовков, без LLM. Выполняется ПОСЛЕ longread/story
6. **sshpass для серверных команд** — credentials из `.env.local`, НЕ интерактивный ssh
7. **Slides — отдельный API endpoint** (`/api/step/slides`), не часть stage абстракции

---

## Документация

| Тема | Документ |
|------|----------|
| Обзор системы | [docs/overview.md](docs/overview.md) |
| Архитектура | [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) |
| Конфигурация | [docs/configuration.md](docs/configuration.md) |
| Pipeline (этапы) | [docs/pipeline/](docs/pipeline/) |
| Stage абстракция | [docs/pipeline/stages.md](docs/pipeline/stages.md) |
| Форматы данных | [docs/data-formats.md](docs/data-formats.md) |
| API сервисов | [docs/api-reference.md](docs/api-reference.md) |
| Развёртывание | [docs/deployment.md](docs/deployment.md) |
| Логирование | [docs/logging.md](docs/logging.md) |
| Тестирование | [docs/testing.md](docs/testing.md) |
| Прокси для Claude | [docs/Прокси для Docker-приложений.md](docs/Прокси%20для%20Docker-приложений.md) |
| Модульная архитектура | [docs/architecture/](docs/architecture/) |
| Требования | [docs/requirements/](docs/requirements/) |
| ADR (решения) | [docs/decisions/](docs/decisions/) |

---

## Workflow

### При планировании (Plan Mode)

**Перед созданием плана изучи архитектуру:**
- `docs/ARCHITECTURE.md` — как устроена система, какие компоненты есть
- `docs/architecture/` — детали затрагиваемых подсистем
- `docs/pipeline/` — ключевая подсистема, этапы обработки
- `docs/decisions/` — почему приняты текущие решения, какие ограничения
- `docs/requirements/` — активные требования на разработку
- `.claude/rules/` — правила модулей, которые будут затронуты

Это критически важно для качественного плана.

### Крупная фича

```
/preflight {задача} → план → реализация → /finalize
```

### Быстрая доработка

```
Читать этот файл → реализация → проверить секцию "После реализации"
```

### Баг

```
Простой (1-2 файла) → исправить напрямую
Сложный → план → реализация
Архитектурный → добавить ограничение сюда
```

---

## После реализации (ОБЯЗАТЕЛЬНО)

<!--
Эта секция — автоматическая замена /finalize для рутинной работы.
Claude выполняет эти проверки после каждого завершённого блока работы.
Для глубокого аудита используй /finalize или /sync-docs.
-->

После каждого завершённого блока работы проверь:

1. **Архитектура изменилась?** → обнови `docs/ARCHITECTURE.md` (обзор)
2. **Реализован модуль/подсистема?** → создай или обнови `docs/architecture/{module}.md`, обнови индекс `docs/architecture/README.md`
3. **Pipeline изменился?** → обнови соответствующий документ в `docs/pipeline/`
4. **Новый паттерн или значимое решение?** → предложи создать ADR в `docs/decisions/`
5. **Структура проекта изменилась?** → обнови секцию "Структура проекта" ниже
6. **Правила `.claude/rules/`:**
   - Новый модуль → нужен новый файл правил или `globs:` в существующем?
   - Изменился паттерн → обновить правило или откатить код?
   - Устаревшее правило → удалить
7. **Edge case или ошибка AI?** → добавь ограничение в секцию выше

> Для полного аудита документации — `/sync-docs`

---

## Структура проекта

```
backend/app/services/             # Сервисы pipeline (incl. description_generator.py)
backend/app/services/ai_clients/  # AI клиенты (v0.17+)
backend/app/services/pipeline/    # Pipeline package (v0.15+)
backend/app/services/stages/      # Stage абстракция (v0.14+)
backend/app/utils/                # Shared utilities (v0.16+)
backend/app/models/               # Pydantic models (schemas.py, cache.py)
backend/app/api/                  # FastAPI endpoints
frontend/src/                     # React + Vite + Tailwind
frontend/src/utils/               # Shared utilities (formatUtils.ts, v0.35+)
config/prompts/                   # LLM промпты
config/glossary.yaml              # Терминология
config/events.yaml                # Типы событий для парсинга
docs/decisions/                   # Architecture Decision Records
docs/pipeline/                    # Документация pipeline (14 файлов)
```

---

## Маршрутизация правил

<!--
Эта секция помогает AI правильно сохранять новые правила.
Когда разработчик говорит "запомни на будущее" — AI определяет куда записать.
-->

Если нужно зафиксировать новое правило:

| Тип | Куда | Пример |
|-----|------|--------|
| Правило pipeline/stages | `.claude/rules/pipeline.md` | "BaseStage — ВСЕГДА наследовать" |
| Правило AI клиентов | `.claude/rules/ai-clients.md` | "НЕ добавлять fallback" |
| Правило API/моделей | `.claude/rules/api.md` | "CamelCaseModel обязателен" |
| Правило контента | `.claude/rules/content.md` | "educational vs leadership" |
| Правило инфраструктуры | `.claude/rules/infrastructure.md` | "sshpass для сервера" |
| Правило frontend | `.claude/rules/frontend.md` | "formatUtils для метрик" |
| Общее ограничение | Секция "Ключевые ограничения" выше | "НИКОГДА не удалять ADR" |
| Архитектурное решение | `docs/decisions/ADR-NNN.md` | "Почему Claude default" |
| Описание системы (обзор) | `docs/ARCHITECTURE.md` | "Добавлен новый компонент" |
| Описание подсистемы | `docs/architecture/{module}.md` | "Как устроен экспорт чанков" |

---

## Разработка

**macOS:** Системный Python защищён — используй `python3 -m venv .venv`. Проверка синтаксиса без venv: `python3 -m py_compile backend/app/...`

**Backend:** `cd backend && python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt`

**Frontend:** `cd frontend && npm install && npm run dev`

**Тестирование:** см. [docs/testing.md](docs/testing.md) — изолированные тесты без Settings для локальной разработки.

---

## Версионирование

Версия в `frontend/package.json`, отображается в UI (`v0.1.0 • 10.01.26 15:30`). Дата/время обновляются автоматически при сборке.

- **patch** (0.1.x) — баг-фиксы, мелкие правки
- **minor** (0.x.0) — новые фичи, заметные улучшения
- **major** (x.0.0) — ломающие изменения, крупные переработки

---

## Текущий статус

| Версия | Ключевые изменения |
|--------|--------------------|
| v0.64 | Импорт MD-транскриптов из MacWhisper, SpeakerInfo |
| v0.63 | HTTPS через Traefik, убран прямой порт бэкенда |
| v0.62 | Description generation moved from Save to Chunk stage |
| v0.60 | BZ2-Bot chunk format, describe_model, split >600w |
| v0.59 | API camelCase serialization, Statistics tab |
| v0.51 | Slides extraction (Claude Vision API) |
| v0.29 | Claude default, fallback удалён |

---

_Entry point для AI. При проблемах — добавь ограничение. Держи < 300 строк. Если > 250 — запусти `/refactor-claude`._
