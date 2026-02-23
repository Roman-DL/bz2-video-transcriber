---
paths:
  - "backend/app/services/rules/**"
  - "backend/app/services/sync/**"
---

# Rules: Rules Engine & Sync Manager

## Модель Rule
- Центральная сущность: `name`, `source_path`, `target_folder_id`, `mode`, `file_pattern`, `recursive`, `polling_interval_min`, `status`, `last_checked`
- Три режима: `once` (разовая), `one-way` (MD→GDoc), `two-way` (MD↔GDoc)
- Default `recursive`: `true` для `once`, `false` для `one-way`/`two-way`

## SQLite — 3 таблицы
- `rules` — конфигурация правил
- `file_mappings` — связь source_path ↔ document_id (UNIQUE по rule_id + source_path)
- `conversion_log` — лог конвертаций (результат, ошибки, время)

## Sync Manager — Polling
- Периодическое сканирование директорий, НЕ inotify/kqueue (SMB/NFS ненадёжен)
- Цикл: для каждого активного правила → проверить interval → scan → detect changes → queue
- Base sleep: 30 секунд между циклами

## Change Detection
- `once` — файл отсутствует в file_mappings → конвертировать
- `one-way` — SHA-256 hash файла изменился → обновить GDoc
- `two-way` — сравнение source_modified_at и target_modified_at → last-modified wins

## Дедупликация
- SHA-256 hash содержимого файла (поле `source_hash` в file_mappings)
- Предотвращает повторную конвертацию при polling если файл не менялся

## Рекурсивный поиск (once)
- Выгрузка в плоскую папку GDrive (без воссоздания структуры директорий)
- При совпадении имён — добавить префикс из имени родительской папки

## Background Worker
- Max 3 concurrent конвертации (Google API rate limits)
- Exponential backoff: 3 попытки при ошибках
- Результат каждой операции — запись в `conversion_log`

## Конфликт resolution (two-way)
- ВСЕГДА last-modified wins — НЕ merge, НЕ manual resolution
- При конфликте — перезаписать старую версию

## Документация
- Подробная архитектура: `docs/architecture/02-rules-engine.md`
