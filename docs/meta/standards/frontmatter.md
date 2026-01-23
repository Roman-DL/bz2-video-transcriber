---
doc_type: reference
ai_scope: none
status: active
created: 2026-01-23
updated: 2026-01-23
tags:
  - documentation
  - meta
  - standards
---

# Frontmatter Standard

> Стандарт метаданных YAML для документов проекта.

---

## Зачем нужен frontmatter

> [!note] Frontmatter — это YAML-блок в начале Markdown-файла
> ```yaml
> ---
> key: value
> ---
> ```

**Преимущества:**
- AI-агенты фильтруют документы по типу и статусу
- Obsidian использует для поиска, графа, dataview
- Автоматизация: скрипты могут обрабатывать метаданные
- Единообразие: понятно, что ожидать от документа

---

## Обязательные поля

### doc_type

Тип документа по [Diátaxis+ Framework](../framework.md).

```yaml
doc_type: reference
```

| Значение | Описание |
|----------|----------|
| `tutorial` | Обучающий материал |
| `how-to` | Руководство по задаче |
| `reference` | Справочная информация |
| `explanation` | Объяснение "почему" |
| `adr` | Architecture Decision Record |
| `proposal` | Предложение/требования |
| `audit` | Аудит/snapshot состояния |
| `moc` | Map of Content |

---

### status

Текущее состояние документа.

```yaml
status: active
```

| Значение | Описание | Действие |
|----------|----------|----------|
| `draft` | В работе | Не использовать как источник истины |
| `active` | Актуален | Основной статус |
| `outdated` | Требует обновления | Обновить или пометить deprecated |
| `deprecated` | Устарел | Перенести в archive/ |
| `archived` | В архиве | Только для истории |

> [!warning] Для ADR используются другие статусы
> `proposed`, `accepted`, `superseded`, `deprecated`
> См. [Diátaxis+ Framework](../framework.md#adr--иммутабельные)

---

### updated

Дата последнего обновления в формате ISO.

```yaml
updated: 2026-01-23
```

> [!tip] Обновляйте при каждом изменении содержимого
> Не обновлять при исправлении опечаток.

---

## Рекомендуемые поля

### audience

Для кого предназначен документ.

```yaml
audience: [developer, ai-agent]
```

| Значение | Описание |
|----------|----------|
| `developer` | Разработчик (человек) |
| `ai-agent` | AI-ассистент (Claude Code и др.) |
| `ops` | DevOps / эксплуатация |

> [!note] Массив или строка
> ```yaml
> audience: developer           # одна аудитория
> audience: [developer, ops]    # несколько
> ```

---

### version

С какой версии проекта документ актуален.

```yaml
version: v0.59+
```

Используйте когда документ привязан к конкретному релизу или функционалу.

---

### created

Дата создания документа.

```yaml
created: 2026-01-23
```

---

### tags

Теги для поиска и категоризации.

```yaml
tags:
  - pipeline
  - api
  - llm
```

> [!tip] Рекомендуемые теги для проекта
> - `pipeline` — этапы обработки
> - `api` — API и эндпоинты
> - `llm` — работа с LLM (Claude, промпты)
> - `frontend` — React, UI
> - `config` — конфигурация
> - `deploy` — деплой, Docker

---

### related

Связанные документы (относительные пути от текущего файла).

```yaml
related:
  - ../architecture.md
  - ../adr/007-remove-fallback-use-claude.md
```

> [!note] Формат ссылок
> Используем относительные markdown-ссылки — они понятны AI, работают в Obsidian, GitHub и VS Code.
> ```markdown
> См. [Architecture](../architecture.md)
> ```

---

## Специальные поля

### ai_scope

Должен ли AI-агент использовать этот документ при работе с кодом.

```yaml
ai_scope: none
```

| Значение | Описание |
|----------|----------|
| `project` | Использовать для работы с проектом (по умолчанию) |
| `none` | Не использовать (мета-документация) |

> [!warning] Только для docs/meta/
> Это поле нужно только для мета-документации, чтобы агенты её игнорировали при работе с кодом проекта.

---

### superseded_by / supersedes

Для ADR — связь с заменяющим/заменённым документом.

```yaml
# В старом ADR
status: superseded
superseded_by: ./015-new-approach.md

# В новом ADR
supersedes: ./007-old-approach.md
```

---

## Полные примеры

### Reference документ

```yaml
---
doc_type: reference
status: active
updated: 2026-01-23
audience: [developer, ai-agent]
version: v0.59+
tags:
  - api
  - reference
---
```

### ADR

```yaml
---
doc_type: adr
status: accepted
created: 2026-01-21
updated: 2026-01-21
tags:
  - architecture
  - llm
related:
  - ./004-ai-client-abstraction.md
---
```

### Proposal

```yaml
---
doc_type: proposal
status: implemented
created: 2026-01-20
updated: 2026-01-23
tags:
  - feature
  - slides
---
```

### Мета-документ

```yaml
---
doc_type: reference
ai_scope: none
status: active
created: 2026-01-23
updated: 2026-01-23
tags:
  - documentation
  - meta
---
```

---

## Валидация

> [!todo] Планируется
> Скрипт для проверки frontmatter на соответствие стандарту.

Минимальная проверка вручную:

```
✓ doc_type — одно из допустимых значений
✓ status — одно из допустимых значений  
✓ updated — формат YYYY-MM-DD
✓ Для docs/meta/ — есть ai_scope: none
```

---

## Миграция существующих документов

### Приоритет 1: Ключевые документы

Добавить frontmatter в первую очередь:

- `docs/overview.md`
- `docs/architecture.md`
- `docs/adr/*.md` (все ADR)
- `docs/pipeline/stages.md`

### Приоритет 2: Справочные

- `docs/api-reference.md`
- `docs/configuration.md`
- `docs/data-formats.md`
- `docs/pipeline/*.md`

### Приоритет 3: Остальные

- `docs/proposals/*`
- `docs/research/*`
- `docs/deployment.md`

> [!tip] Промпт для Claude Code
> ```
> Добавь стандартный frontmatter во все .md файлы в docs/.
> Используй стандарт из docs/meta/standards/frontmatter.md.
> Определи doc_type по содержимому и расположению.
> Определи status по baseline-2026-01.md.
> Сохрани существующие поля (created, tags, related).
> ```

---

## Changelog

| Дата | Изменение |
|------|-----------|
| 2026-01-23 | Создан документ |
