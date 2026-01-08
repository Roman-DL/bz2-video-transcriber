# Документация bz2-video-transcriber

Система автоматической транскрипции и саммаризации видеозаписей для БЗ 2.0.

## Навигация

### Основные документы

| Документ | Описание |
|----------|----------|
| [architecture.md](architecture.md) | Схема системы, компоненты, Docker |
| [api-reference.md](api-reference.md) | HTTP API для Ollama и Whisper |
| [data-formats.md](data-formats.md) | Форматы входных/выходных файлов |
| [deployment.md](deployment.md) | Развёртывание на TrueNAS |

### Pipeline обработки

| Этап | Документ | Описание |
|------|----------|----------|
| Обзор | [pipeline/README.md](pipeline/README.md) | Схема и общий flow |
| 1 | [pipeline/01-parse.md](pipeline/01-parse.md) | Парсинг имени файла |
| 2 | [pipeline/02-transcribe.md](pipeline/02-transcribe.md) | Whisper транскрипция |
| 3 | [pipeline/03-clean.md](pipeline/03-clean.md) | Очистка LLM + глоссарий |
| 4 | [pipeline/04-chunk.md](pipeline/04-chunk.md) | Семантический chunking |
| 5 | [pipeline/05-summarize.md](pipeline/05-summarize.md) | Саммаризация + классификация |
| 6 | [pipeline/06-save.md](pipeline/06-save.md) | Сохранение файлов |
| - | [pipeline/error-handling.md](pipeline/error-handling.md) | Обработка ошибок |

### Справочные материалы

| Документ | Описание |
|----------|----------|
| [reference/terminology.md](reference/terminology.md) | Глоссарий терминологии Herbalife |

### Разработка

| Документ | Описание |
|----------|----------|
| [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) | План реализации (фазы 0-13) |

## Быстрые ссылки

- **Промпты:** [`config/prompts/`](../config/prompts/)
- **Глоссарий:** [`config/glossary.yaml`](../config/glossary.yaml)
- **Сервисы:** [`backend/app/services/`](../backend/app/services/)
