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
| [web-ui.md](web-ui.md) | Документация Web UI |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Процесс разработки новых функций |

## Pipeline обработки

| Этап | Документ | Описание |
|------|----------|----------|
| Обзор | [pipeline/README.md](pipeline/README.md) | Схема и общий flow |
| 1 | [pipeline/01-parse.md](pipeline/01-parse.md) | Парсинг имени файла |
| 2 | [pipeline/02-transcribe.md](pipeline/02-transcribe.md) | Whisper транскрипция |
| 3 | [pipeline/03-clean.md](pipeline/03-clean.md) | Очистка LLM + глоссарий |
| 4 | [pipeline/04-chunk.md](pipeline/04-chunk.md) | Семантический chunking |
| 5 | [pipeline/05-summarize.md](pipeline/05-summarize.md) | Саммаризация + классификация |
| 6 | [pipeline/06-save.md](pipeline/06-save.md) | Сохранение файлов |
| 7 | [pipeline/07-orchestrator.md](pipeline/07-orchestrator.md) | Оркестрация pipeline |
| 8 | [pipeline/08-api.md](pipeline/08-api.md) | FastAPI endpoints |
| - | [pipeline/error-handling.md](pipeline/error-handling.md) | Обработка ошибок |

## Справочники

| Документ | Описание |
|----------|----------|
| [api-reference.md](api-reference.md) | HTTP API для Ollama и Whisper |
| [data-formats.md](data-formats.md) | Форматы входных/выходных файлов |
| [reference/terminology.md](reference/terminology.md) | Глоссарий терминологии Herbalife |

## Гайдлайны

| Документ | Описание |
|----------|----------|
| [DOCUMENTATION_GUIDELINES.md](DOCUMENTATION_GUIDELINES.md) | Правила документирования кода |

## Быстрые ссылки

- **Промпты:** [`config/prompts/`](../config/prompts/)
- **Глоссарий:** [`config/glossary.yaml`](../config/glossary.yaml)
- **Сервисы:** [`backend/app/services/`](../backend/app/services/)
