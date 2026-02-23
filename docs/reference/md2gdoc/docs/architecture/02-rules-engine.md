# 02 — Rules Engine & Sync Manager

Система правил (rules) и менеджер синхронизации: хранение правил, мониторинг папок, определение изменений, запуск конвертаций.

**Обзор архитектуры:** [ARCHITECTURE.md](../ARCHITECTURE.md)

---

## Обзор

```
┌──────────────────────────────────────────────────────────┐
│                    Rules Engine                          │
│                                                          │
│  ┌──────────┐   ┌──────────────┐   ┌─────────────────┐   │
│  │ CRUD API │──▶│ Rules Store  │──▶│  Sync Manager   │   │
│  │          │   │ (SQLite)     │   │  (background)   │   │
│  └──────────┘   └──────────────┘   └────────┬────────┘   │
│                                             │            │
│                       ┌─────────────────────┤            │
│                       ▼                     ▼            │
│              ┌────────────────┐    ┌─────────────────┐   │
│              │ Polling Loop   │    │ Change Detector │   │
│              │ (per-rule)     │    │ (hash compare)  │   │
│              └────────────────┘    └─────────────────┘   │
└──────────────────────────────────────────────────────────┘
```

---

## Модель Rule

### Поля

| Поле | Тип | Default | Описание |
|------|-----|---------|----------|
| `id` | TEXT (UUID) | auto | Уникальный идентификатор |
| `name` | TEXT | required | Человекочитаемое название |
| `source_path` | TEXT | required | Локальный путь (серверный или SMB/NFS mount) |
| `target_folder_id` | TEXT | required | ID папки на Google Drive |
| `mode` | TEXT | `'once'` | `once` / `one-way` / `two-way` |
| `file_pattern` | TEXT | `'*.md'` | Glob-паттерн для фильтрации |
| `recursive` | BOOLEAN | зависит от mode | Поиск в подпапках |
| `polling_interval_min` | INTEGER | `5` | Интервал опроса (1–60 мин) |
| `status` | TEXT | `'active'` | `active` / `paused` |
| `last_checked` | TIMESTAMP | NULL | Время последней проверки |
| `created_at` | TIMESTAMP | auto | Время создания |

### Default для `recursive`

| Режим | Default `recursive` | Обоснование |
|-------|-------------------|-------------|
| `once` | `true` | Лонгриды хранятся в подпапках по темам |
| `one-way` | `false` | Для вложенных папок — отдельные правила |
| `two-way` | `false` | Для вложенных папок — отдельные правила |

### Валидация при создании

- `source_path` — путь существует и доступен на чтение
- `target_folder_id` — папка доступна через Service Account
- `file_pattern` — валидный glob
- `polling_interval_min` — в диапазоне 1–60
- `mode` — один из `once`, `one-way`, `two-way`

---

## SQL Schema

```sql
CREATE TABLE rules (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  source_path TEXT NOT NULL,
  target_folder_id TEXT NOT NULL,
  mode TEXT NOT NULL DEFAULT 'once',
  file_pattern TEXT DEFAULT '*.md',
  recursive BOOLEAN DEFAULT TRUE,
  polling_interval_min INTEGER DEFAULT 5,
  status TEXT DEFAULT 'active',
  last_checked TIMESTAMP,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE file_mappings (
  id TEXT PRIMARY KEY,
  rule_id TEXT NOT NULL REFERENCES rules(id),
  source_path TEXT NOT NULL,
  source_hash TEXT NOT NULL,
  document_id TEXT NOT NULL,
  document_url TEXT NOT NULL,
  source_modified_at TIMESTAMP,
  target_modified_at TIMESTAMP,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(rule_id, source_path)
);

CREATE TABLE conversion_log (
  id TEXT PRIMARY KEY,
  rule_id TEXT REFERENCES rules(id),  -- NULL для ручных конвертаций
  source_path TEXT NOT NULL,
  document_url TEXT,
  status TEXT NOT NULL,               -- 'success' / 'error'
  error_message TEXT,
  duration_ms INTEGER,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## Sync Manager

### Polling Loop

Фоновый процесс, запускается при старте приложения:

```
loop:
  for rule in active_rules:
    if now - rule.last_checked >= rule.polling_interval:
      files = scan_directory(rule.source_path, rule.file_pattern, rule.recursive)
      changed = detect_changes(files, rule)
      for file in changed:
        queue_conversion(file, rule)
      rule.last_checked = now
  sleep(30s)  # базовый интервал проверки
```

### Change Detection

Определение новых/изменённых файлов по хешу содержимого:

| Режим | Что проверяем | Как определяем изменение |
|-------|--------------|------------------------|
| `once` | Новые файлы | Файл отсутствует в `file_mappings` для этого правила |
| `one-way` | Новые + изменённые | Hash файла не совпадает с `source_hash` в `file_mappings` |
| `two-way` | MD + GDoc | Сравнение `source_modified_at` и `target_modified_at` |

### Дедупликация

- Хеш: SHA-256 содержимого файла
- Файл с тем же хешем не конвертируется повторно
- При изменении содержимого — хеш обновляется, запускается переконвертация (для `one-way`/`two-way`)

### Рекурсивный поиск (`once` mode)

```
source_path: /mnt/main/work/bz2/video/archive/
recursive: true
file_pattern: longread.md

Сканирование:
  /archive/topic-1/longread.md  → найден
  /archive/topic-2/longread.md  → найден
  /archive/topic-3/slides/      → пропущен (не .md)

Выгрузка на GDrive: плоская папка (без вложенности)
  Google Drive: "БЗ 2.0 / Лонгриды/"
    ├── topic-1-longread.md   (или с оригинальным именем, если уникально)
    └── topic-2-longread.md
```

> При совпадении имён — добавляется префикс из имени родительской папки.

---

## Режимы работы

### `once` — разовая конвертация

```
1. scan_directory() → найти файлы по паттерну
2. filter: файлы НЕ в file_mappings → новые
3. convert(file) → создать Google Doc
4. save file_mapping (source_path, hash, document_id)
5. Повторные изменения файла — игнорируются (mapping уже есть)
```

### `one-way` — односторонняя синхронизация

```
1. scan_directory() → найти файлы по паттерну
2. Для каждого файла:
   a. Нет в file_mappings → новый → convert + создать mapping
   b. Есть, hash изменился → update Google Doc + обновить mapping
   c. Есть, hash не изменился → skip
3. Изменения в Google Doc игнорируются
```

### `two-way` — двусторонняя синхронизация

```
1. scan_directory() → найти файлы по паттерну
2. poll Google Drive → проверить target_modified_at для mapped файлов
3. Для каждого файла:
   a. MD изменился, GDoc нет → update GDoc
   b. GDoc изменился, MD нет → reverse convert → update MD
   c. Оба изменились → last-modified wins (логируем конфликт)
   d. Ничего не изменилось → skip
```

### Conflict Resolution (`two-way`)

- Стратегия: **last-modified wins**
- Без дополнительного UI для ручного разрешения
- Факт конфликта записывается в `conversion_log` с пометкой
- Проигравшая сторона перезаписывается

---

## API Endpoints

```
GET    /api/rules                 # Список всех правил
POST   /api/rules                 # Создать правило
PATCH  /api/rules/:id             # Обновить правило
DELETE /api/rules/:id             # Удалить правило
POST   /api/rules/:id/pause       # Приостановить
POST   /api/rules/:id/resume      # Возобновить
POST   /api/rules/:id/trigger     # Ручной запуск проверки

POST   /api/convert               # Ручная разовая конвертация (без правила)

GET    /api/logs                   # История операций
GET    /api/logs?rule_id=...       # Логи конкретного правила
```

---

## Фоновый Worker

- Очередь конвертаций: максимум **3 одновременных** (rate limits Google API)
- При ошибке — retry с exponential backoff (3 попытки)
- Результат каждой операции — в `conversion_log`
- Worker запускается как background task при старте FastAPI

---

_Обновлять при изменении логики правил или синхронизации._
