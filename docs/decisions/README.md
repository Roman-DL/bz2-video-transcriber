# Architecture Decision Records (ADR)

Архитектурные решения проекта bz2-video-transcriber.

> ADR иммутабельны — не изменять принятые решения. Для отмены создать новый ADR со статусом `supersedes`.

## Индекс

| ADR | Статус | Описание |
|-----|--------|----------|
| [001](001-stage-abstraction.md) | accepted | Stage абстракция |
| [002](002-pipeline-decomposition.md) | accepted | Декомпозиция pipeline |
| [003](003-shared-utils.md) | accepted | Shared utilities |
| [004](004-ai-client-abstraction.md) | accepted | AI client абстракция |
| [005](005-result-caching.md) | accepted | Stage result cache |
| [006](006-cloud-model-integration.md) | accepted | Cloud model integration (Claude) |
| [007](007-remove-fallback-use-claude.md) | accepted | Remove fallback, use Claude |
| [008](008-external-prompts.md) | accepted | External prompts |
| [009](009-extended-metrics.md) | accepted | Extended metrics (v0.42+) |
| [010](010-slides-integration.md) | accepted | Slides integration (v0.51+) |
| [011](011-processing-mode-separation.md) | accepted | Processing mode separation |
| [012](012-statistics-tab.md) | accepted | Statistics tab (v0.58+) |
| [013](013-api-camelcase-serialization.md) | accepted | API camelCase serialization (v0.59+) |

## Создание нового ADR

```bash
# Формат: NNN-short-name.md
cp docs/decisions/013-api-camelcase-serialization.md docs/decisions/014-new-decision.md
```

Обязательные поля: `status`, `date`, `context`, `decision`, `consequences`.
