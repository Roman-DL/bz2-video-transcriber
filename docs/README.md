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
| [architecture.md](architecture.md) | Техническая архитектура, схемы |
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
| [reference/terminology.md](reference/terminology.md) | Глоссарий терминологии |
| [reference/progress-calibration.md](reference/progress-calibration.md) | Калибровка прогресса |

## Architecture Decision Records

| ADR | Описание |
|-----|----------|
| [001](adr/001-stage-abstraction.md) | Stage абстракция |
| [002](adr/002-pipeline-decomposition.md) | Декомпозиция pipeline |
| [003](adr/003-shared-utils.md) | Shared utilities |
| [004](adr/004-ai-client-abstraction.md) | AI client абстракция |
| [005](adr/005-result-caching.md) | Stage result cache |
| [006](adr/006-cloud-model-integration.md) | Cloud model integration (Claude) |
| [007](adr/007-remove-fallback-use-claude.md) | Remove fallback, use Claude |
| [008](adr/008-external-prompts.md) | External prompts |
| [009](adr/009-extended-metrics.md) | Extended metrics (v0.42+) |
| [010](adr/010-slides-integration.md) | Slides integration (v0.51+) |
| [011](adr/011-processing-mode-separation.md) | Processing mode separation |
| [012](adr/012-statistics-tab.md) | Statistics tab (v0.58+) |
| [013](adr/013-api-camelcase-serialization.md) | API camelCase serialization (v0.59+) |

## Гайдлайны

| Документ | Описание |
|----------|----------|
| [DOCUMENTATION_GUIDELINES.md](DOCUMENTATION_GUIDELINES.md) | Правила документирования кода |

## Быстрые ссылки

- **Конфигурация:** [configuration.md](configuration.md)
- **Промпты:** [`config/prompts/`](../config/prompts/)
- **Глоссарий:** [`config/glossary.yaml`](../config/glossary.yaml)
- **Сервисы:** [`backend/app/services/`](../backend/app/services/)
