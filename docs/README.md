---
doc_type: moc
status: active
updated: 2026-02-10
audience: [developer, ai-agent]
tags:
  - documentation
  - navigation
---

# Документация bz2-video-transcriber

Система автоматической транскрипции и саммаризации видеозаписей для БЗ 2.0.

## Быстрый старт

| Документ | Описание |
|----------|----------|
| [overview.md](overview.md) | Обзор системы — что это и зачем |
| [deployment.md](deployment.md) | Как запустить |

## Архитектура и разработка

| Документ | Описание |
|----------|----------|
| [ARCHITECTURE.md](ARCHITECTURE.md) | Техническая архитектура, схемы |
| [architecture/](architecture/) | Индекс архитектурной документации |
| [configuration.md](configuration.md) | Конфигурация моделей, промптов, pricing |
| [web-ui.md](web-ui.md) | Документация Web UI |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Процесс разработки новых функций |

## Pipeline обработки

| Этап | Документ | Описание |
|------|----------|----------|
| Обзор | [pipeline/README.md](pipeline/README.md) | Схема и общий flow |
| Stages | [pipeline/stages.md](pipeline/stages.md) | Stage абстракция (v0.14+) |
| 1 | [pipeline/01-parse.md](pipeline/01-parse.md) | Парсинг имени файла |
| 2 | [pipeline/02-transcribe.md](pipeline/02-transcribe.md) | Whisper транскрипция |
| 3 | [pipeline/03-clean.md](pipeline/03-clean.md) | Очистка LLM + глоссарий |
| 3a | [pipeline/03a-slides.md](pipeline/03a-slides.md) | Извлечение текста со слайдов |
| 4 | [pipeline/04-chunk.md](pipeline/04-chunk.md) | H2 chunking (v0.25+, детерминированный) |
| 5 | [pipeline/05-longread.md](pipeline/05-longread.md) | Генерация лонгрида (educational) |
| 5b | [pipeline/05b-story.md](pipeline/05b-story.md) | Генерация истории (leadership) |
| 6 | [pipeline/06-summarize.md](pipeline/06-summarize.md) | Саммаризация (конспект) |
| 7 | [pipeline/07-save.md](pipeline/07-save.md) | Сохранение файлов |
| 8 | [pipeline/08-orchestrator.md](pipeline/08-orchestrator.md) | Оркестрация pipeline |
| 9 | [pipeline/09-api.md](pipeline/09-api.md) | FastAPI endpoints |
| - | [pipeline/error-handling.md](pipeline/error-handling.md) | Обработка ошибок |

## Справочники

| Документ | Описание |
|----------|----------|
| [api-reference.md](api-reference.md) | HTTP API endpoints |
| [data-formats.md](data-formats.md) | Форматы файлов, метрики (v0.42+) |
| [logging.md](logging.md) | Система логирования |
| [testing.md](testing.md) | Тестирование |
| [model-testing.md](model-testing.md) | Тестирование моделей |
| [reference/](reference/) | Справочные материалы |

## Решения и планирование

| Документ | Описание |
|----------|----------|
| [decisions/](decisions/) | Architecture Decision Records (13 ADR) |
| [requirements/](requirements/) | Спецификации требований |
| [plans/](plans/) | Планы реализации |

## Гайдлайны

| Документ | Описание |
|----------|----------|
| [DOCUMENTATION_GUIDELINES.md](DOCUMENTATION_GUIDELINES.md) | Правила документирования кода |
| [reference/diataxis-framework.md](reference/diataxis-framework.md) | Фреймворк Diátaxis |
| [reference/standards/](reference/standards/) | Стандарты документации |

## Быстрые ссылки

- **Конфигурация:** [configuration.md](configuration.md)
- **Промпты:** [`config/prompts/`](../config/prompts/)
- **Глоссарий:** [`config/glossary.yaml`](../config/glossary.yaml)
- **Сервисы:** [`backend/app/services/`](../backend/app/services/)
