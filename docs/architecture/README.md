# Архитектурная документация

Детальная архитектурная документация проекта bz2-video-transcriber.

> **Обзор архитектуры:** [ARCHITECTURE.md](../ARCHITECTURE.md) — точка входа

## Подсистемы

| Документ | Описание |
|----------|----------|
| [pipeline/](../pipeline/) | Pipeline обработки видео (14 документов) |
| [pipeline/stages.md](../pipeline/stages.md) | Stage абстракция |
| [pipeline/08-orchestrator.md](../pipeline/08-orchestrator.md) | Оркестратор |

## Решения

Архитектурные решения (ADR): [decisions/](../decisions/)

## Справочники

| Документ | Описание |
|----------|----------|
| [configuration.md](../configuration.md) | Конфигурация моделей, промптов, pricing |
| [data-formats.md](../data-formats.md) | Форматы файлов и метрик |
| [api-reference.md](../api-reference.md) | HTTP API endpoints |
| [deployment.md](../deployment.md) | Развёртывание и Docker |
