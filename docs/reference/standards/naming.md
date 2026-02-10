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

# Naming Conventions

> Соглашения об именовании файлов, папок и языке документов.

---

## Язык документов

| Область | Язык | Примеры |
|---------|------|---------|
| Мета-документация (`docs/reference/`) | Русский | MOC, workflows, standards |
| Проектная документация (`docs/`) | Английский | ARCHITECTURE.md, adr/*.md |
| Комментарии в коде | Английский | docstrings, TODO |

> [!note] Язык содержимого ≠ язык названия файла
> Файл может называться `framework.md`, но содержимое внутри — на русском.

---

## Именование файлов

### MOC документы

Формат: `MOC - Название на русском.md`

```
MOC - Управление документацией.md
MOC - Архитектура системы.md
```

> [!tip] Почему так
> MOC — точки входа для человека, русское название сразу понятно.

---

### Остальные документы

Формат: `kebab-case.md`

```
framework.md
frontmatter.md
doc-sync.md
arch-checker.md
baseline-2026-01.md
```

**Правила:**
- Только латиница, цифры, дефис
- Нижний регистр
- Без пробелов и подчёркиваний
- Расширение `.md`

> [!warning] Избегайте
> - `Framework.md` — заглавные буквы
> - `front_matter.md` — подчёркивания (если в папке уже kebab-case)
> - `фреймворк.md` — кириллица в названии
> - `framework document.md` — пробелы

---

### ADR

Формат: `NNN-краткое-название.md`

```
001-stage-abstraction.md
007-remove-fallback-use-claude.md
013-api-camelcase-serialization.md
```

**Правила:**
- Трёхзначный номер с ведущими нулями
- После номера — дефис
- Краткое описание решения на английском

---

### Proposals

Формат: `краткое-название-requirements.md` или `краткое-название.md`

```
slides-integration-requirements.md
transcriptor-v2-requirements.md
```

---

### Audits

Формат: `тип-YYYY-MM-DD.md`

```
baseline-2026-01-23.md
baseline-2026-02-15.md
security-audit-2026-03-01.md
```

> [!note] Почему полная дата
> При активной разработке может быть несколько аудитов в месяц.

---

## Именование папок

Формат: `kebab-case` или короткие английские слова

```
docs/
├── meta/
│   ├── standards/
│   ├── workflows/
│   ├── agents/
│   └── artifacts/
├── pipeline/
├── adr/
├── proposals/
├── research/
├── archive/
└── audit/
```

> [!note] Папки всегда на английском
> Даже для мета-документации — проще для навигации в терминале и скриптах.

---

## Формат ссылок

Используем относительные markdown-ссылки:

```markdown
См. [Architecture](../ARCHITECTURE.md)
См. [ADR-007](../decisions/007-remove-fallback-use-claude.md)
```

**Почему:**
- AI понимает однозначно
- Работает в Obsidian, GitHub, VS Code
- Нет коллизий имён (в отличие от `[[architecture]]`)

> [!warning] Не использовать
> ```markdown
> [[architecture]]           # Wiki-ссылки — коллизии имён
> [Architecture](architecture)  # Без расширения
> ```

---

## Сводная таблица

| Тип | Формат | Пример |
|-----|--------|--------|
| MOC | `MOC - Название.md` | `MOC - Управление документацией.md` |
| Обычный документ | `kebab-case.md` | `framework.md` |
| ADR | `NNN-название.md` | `007-remove-fallback.md` |
| Proposal | `название-requirements.md` | `slides-integration-requirements.md` |
| Audit | `тип-YYYY-MM-DD.md` | `baseline-2026-01-23.md` |
| Папка | `kebab-case` | `standards/`, `workflows/` |

---

## Примеры правильного именования

```
docs/
├── meta/
│   ├── MOC - Управление документацией.md    ✓
│   ├── framework.md                          ✓
│   ├── standards/
│   │   ├── frontmatter.md                    ✓
│   │   └── naming.md                         ✓
│   └── workflows/
│       └── update.md                         ✓
├── ARCHITECTURE.md                           ✓
├── api-reference.md                          ✓
├── adr/
│   ├── 001-stage-abstraction.md              ✓
│   └── 013-api-camelcase-serialization.md    ✓
├── proposals/
│   └── transcriptor-v2-requirements.md       ✓
└── audit/
    ├── baseline-2026-01-23.md                ✓
    └── architecture-summary.md               ✓
```

---

## Changelog

| Дата | Изменение |
|------|-----------|
| 2026-01-23 | Формат даты для audit изменён на YYYY-MM-DD |
| 2026-01-23 | Создан документ |
