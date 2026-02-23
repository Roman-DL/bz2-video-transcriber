# md2gdoc — Архитектура

**Версия:** 1.0
**Обновлено:** 2026-02-23

> **Требования:** [PROJECT-SPEC.md](PROJECT-SPEC.md) — что и зачем
> **Детали:** [architecture/](architecture/) | [decisions/](decisions/)

---

## Обзор

Веб-сервис конвертации и синхронизации Markdown файлов с Google Docs. Ядро системы — **правила (rules)**, каждое из которых связывает локальную папку с папкой на Google Drive и определяет режим обработки: разовая конвертация, односторонняя или двусторонняя синхронизация.

---

## Архитектурная схема

```
                         ┌──────────────────────────────────────┐
                         │         Admin Panel (Web UI)         │
                         │   правила, логи, статус, настройки   │
                         └─────────────────┬────────────────────┘
                                           │ HTTP API
                              ┌────────────┴────────────────┐
                              │      md2gdoc Service        │
                              │        (TrueNAS)            │
                              │                             │
                              │  ┌───────────────────────┐  │
                              │  │    Rules Engine       │  │
                              │  │  CRUD, валидация,     │  │
                              │  │  управление режимами  │  │
                              │  └───────────┬───────────┘  │
                              │              │              │
                              │  ┌───────────┴───────────┐  │
                              │  │   Sync Manager        │  │
                              │  │  polling (periodic)   │  │
                              │  │  change detection     │  │
                              │  │  conflict resolution  │  │
                              │  └───────────┬───────────┘  │
                              │              │              │
┌───────────────────┐         │  ┌───────────┴───────────┐  │     ┌──────────────────┐
│ Server folder     │────────▶│  │    Converter          │  │────▶│   Google Drive   │
│ /mnt/.../archive/ │         │  │  MD → HTML            │  │     │  (Google Doc)    │
├───────────────────┤         │  │  [Image Resolution]   │  │     │  (Images)       │
│ Mac (SMB/NFS)     │────────▶│  │  HTML → GDoc upload   │  │     │                  │
│ /mnt/obsidian/    │         │  │  GDoc → MD (two-way)  │  │◀────│                  │
└───────────────────┘         │  └───────────────────────┘  │     └──────────────────┘
                              │                             │
                              └─────────────────────────────┘
```

---

## Компоненты

| Компонент | Технология | Назначение |
|-----------|------------|------------|
| **Admin Panel** | React + Vite + Tailwind | Управление правилами, логи, настройки, быстрая конвертация |
| **Backend** | Python, FastAPI | HTTP API, оркестрация, фоновый worker |
| **Rules Engine** | SQLite + CRUD API | Хранение и управление правилами |
| **Sync Manager** | Polling (periodic scan) | Мониторинг папок, определение изменений, запуск конвертаций |
| **Converter** | Python-Markdown/mistune | MD → HTML → GDoc (прямая), GDoc → MD (обратная) |
| **Google Drive Client** | google-api-python-client | Upload, update, export документов через Service Account |

> Детали по каждому компоненту: [architecture/](architecture/)

---

## Потоки данных

```
MD → GDoc (прямая конвертация):
  MD → [Parse frontmatter] → [Convert MD → HTML] → [Image Resolution*] → Upload as Google Doc

GDoc → MD (обратная конвертация, two-way):
  Export GDoc as HTML → [Detect callouts] → [Restore image links] → Convert HTML → MD

* Image Resolution — заложена в архитектуре, MVP: skip + warning
```

---

## Структура проекта (предварительная)

```
md2gdoc/
├── backend/
│   ├── app/
│   │   ├── api/              # FastAPI endpoints
│   │   ├── models/           # Pydantic models, DB schemas
│   │   ├── services/
│   │   │   ├── converter/    # MD↔HTML↔GDoc конвертация
│   │   │   ├── google/       # Google Drive API client
│   │   │   ├── rules/        # Rules Engine
│   │   │   └── sync/         # Sync Manager (polling, change detection)
│   │   └── utils/            # Shared utilities
│   ├── requirements.txt
│   └── main.py
├── frontend/
│   └── src/                  # React + Vite + Tailwind
├── config/
│   └── service-account.json  # Google Service Account key
├── data/
│   └── md2gdoc.db            # SQLite database
├── docker-compose.yml
└── Dockerfile
```

---

## Технические ограничения

| Ограничение | Причина |
|-------------|---------|
| Polling вместо inotify/kqueue | Надёжность на SMB/NFS mount'ах |
| 3 одновременных конвертации | Rate limits Google API (300 req/min) |
| 10 МБ макс. размер MD файла | Ограничение Google Drive API |
| Конфликты: last-modified wins | Простота; merge-уровень — на будущее |
| Image Resolution отложена | MVP без загрузки изображений, placeholder + warning |

---

## Связанные документы

| Документ | Описание |
|----------|----------|
| [PROJECT-SPEC.md](PROJECT-SPEC.md) | Спецификация проекта (требования, scope, решения) |
| [architecture/](architecture/) | Детали по подсистемам |
| [decisions/](decisions/) | Architecture Decision Records |

---

_Документ описывает КАК устроена система. Для деталей по подсистемам — см. architecture/._
