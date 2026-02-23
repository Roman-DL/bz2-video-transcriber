# md2gdoc — Обзор системы

Веб-сервис для конвертации Markdown-файлов в Google Docs с поддержкой двусторонней синхронизации.

## Что делает

Автоматизирует преобразование `.md` файлов (Obsidian vault, документация) в Google Docs и обратно. Избавляет от ручной конвертации (5-10 минут на документ) и зависимости от платных сервисов (CloudConvert).

## Три режима работы

- **once** — разовая конвертация всех новых файлов из папки в Google Drive
- **one-way** — постоянный мониторинг: изменения в MD → обновляют Google Doc
- **two-way** — двусторонняя синхронизация: изменения в любом направлении синхронизируются

## Технологический стек

| Компонент | Технология |
|-----------|------------|
| Backend | Python, FastAPI |
| Frontend | React + Vite + Tailwind |
| БД | SQLite |
| MD → HTML | Python-Markdown / mistune |
| File watcher | Polling (periodic scan) |
| Google API | google-api-python-client (Service Account) |
| Deploy | Docker, Traefik |

## Среда выполнения

TrueNAS (Docker). Исходные папки — локальная FS сервера или SMB/NFS mount (например, Obsidian vault с Mac).

## Подробнее

- [PROJECT-SPEC.md](PROJECT-SPEC.md) — полная спецификация (требования, scope, решения)
- [ARCHITECTURE.md](ARCHITECTURE.md) — техническая архитектура (компоненты, структура, ограничения)
- [architecture/](architecture/) — детали по модулям (converter, rules engine, Google Drive)
