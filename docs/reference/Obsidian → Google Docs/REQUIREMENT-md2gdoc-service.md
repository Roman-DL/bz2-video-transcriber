# md2gdoc — Сервис конвертации Markdown → Google Docs

> Автоматическая конвертация Markdown файлов в Google Docs с мониторингом папок и административной панелью

**Статус:** Draft
**Дата:** 2026-02-23
**Версии:** v0.1 — v1.0 (план)

---

## 1. Проблема

Для загрузки образовательных материалов (лонгридов) в базу знаний БЗ 2.0 требуется ссылка на Google документ. Сейчас конвертация из Markdown выполняется вручную.

**Текущая ситуация:**
- Pipeline bz2-video-transcriber генерирует лонгриды в формате `.md`
- Для загрузки в БЗ нужен Google Doc со ссылкой
- Процесс: открыть MD в Obsidian → режим просмотра → скопировать → создать Google Doc → вставить → получить ссылку
- Каждый документ — 5-10 минут ручной работы

**Почему это проблема:**
- Ручной процесс занимает время и подвержен ошибкам
- Форматирование теряется при копировании (каллауты, таблицы)
- Процесс не масштабируется при увеличении количества материалов
- Предыдущая попытка автоматизации через n8n оказалась нестабильной и дорогой (CloudConvert)

---

## 2. Решение

Самостоятельный веб-сервис, который мониторит папки (локальные и на Google Drive) и автоматически конвертирует Markdown файлы в Google Docs.

### Ключевые идеи

1. **MD → HTML → Google Doc** — конвертируем MD в HTML, загружаем на Google Drive с автоконвертацией в Google Doc (бесплатно, без внешних API)
2. **Мониторинг папок** — отслеживание локальных директорий (watchdog) и Google Drive папок (polling API) на появление новых/изменённых `.md` файлов
3. **Административная панель** — веб-интерфейс для настройки папок, просмотра логов конвертации, управления параметрами
4. **Универсальность** — работает с любыми MD файлами, не привязан к конкретному pipeline

### Архитектура

```
                    ┌─────────────────────────┐
                    │    Admin Panel (Web UI)  │
                    │  настройки, логи, статус │
                    └───────────┬─────────────┘
                                │ HTTP API
┌──────────────┐    ┌───────────┴─────────────┐    ┌──────────────────┐
│ Local Folder │───▶│      md2gdoc Service     │───▶│   Google Drive   │
│  (watchdog)  │    │                          │    │  (Google Doc)    │
├──────────────┤    │  1. Detect new .md       │    │                  │
│ Google Drive │───▶│  2. Parse MD → HTML      │    │  → Ссылка на     │
│  (polling)   │    │  3. Upload as Google Doc  │    │    документ      │
└──────────────┘    │  4. Log result            │    └──────────────────┘
                    └──────────────────────────┘
```

### Что берём из референсного проекта

| Компонент | Источник | Что берём |
|-----------|----------|-----------|
| **Парсинг каллаутов** | `obsidian_to_gdocs.py`, n8n Code нода | Regex-паттерны для Obsidian callouts `> [!type]`, конвертация в HTML-блоки |
| **Парсинг тегов** | `topaz_nord_constants.js` | Regex для `#tag` → форматированный текст |
| **Структура HTML** | n8n Code нода "Add Header Colors" | Обёртка в HTML-документ с базовыми CSS стилями |
| **Типы каллаутов** | `topaz_nord_constants.js` | 13 типов + алиасы (note, info, tip, warning, danger и др.) |
| **Google Drive upload** | n8n workflow (концепция) | Подход: upload с `mimeType: application/vnd.google-apps.document` |

### Что НЕ берём

| Компонент | Причина |
|-----------|---------|
| n8n архитектура | Заменяется собственным сервисом |
| CloudConvert | Заменяется бесплатной автоконвертацией Google Drive |
| Topaz-Nord цвета | Устаревшая тема, используем нейтральные стили |
| Pandoc зависимость | Заменяется Python-библиотекой для MD → HTML |
| Hardcoded credentials | Заменяется конфигурацией через admin panel |

---

## 3. Пользовательский сценарий

### Сценарий 1: Первоначальная настройка

```
1. Пользователь открывает admin panel (https://md2gdoc.home)
2. Настраивает Google OAuth credentials
3. Добавляет watched folder:
   - Тип: локальная папка
   - Путь: /mnt/main/work/bz2/video/archive/
   - Целевая папка Google Drive: "БЗ 2.0 / Лонгриды"
   - Фильтр: longread.md
4. Включает мониторинг
5. Результат: сервис начинает отслеживать папку
```

### Сценарий 2: Автоматическая конвертация

```
1. Pipeline bz2-video-transcriber сохраняет longread.md в /archive/
2. Сервис md2gdoc обнаруживает новый файл (watchdog)
3. Конвертирует MD → HTML (с поддержкой каллаутов, таблиц, форматирования)
4. Загружает HTML на Google Drive → автоконвертация в Google Doc
5. Записывает в лог: файл, ссылка на Google Doc, время
6. Результат: Google Doc доступен по ссылке
```

### Сценарий 3: Ручная конвертация

```
1. Пользователь открывает admin panel
2. Загружает MD файл через drag & drop или указывает путь
3. Выбирает целевую папку на Google Drive
4. Нажимает "Конвертировать"
5. Результат: получает ссылку на Google Doc
```

---

## 4. UI

### Главная страница (Dashboard)

```
┌──────────────────────────────────────────────────────────────┐
│  md2gdoc                           [Settings] [Logs]         │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  Watched Folders                              [+ Добавить]   │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │ 📁 /archive/**/ longread.md                    [Active] │ │
│  │    → Google Drive: БЗ 2.0 / Лонгриды                   │ │
│  │    Последняя конвертация: 23.02.2026 14:30              │ │
│  ├─────────────────────────────────────────────────────────┤ │
│  │ ☁️ Google Drive: Obsidian/Команда/*.md       [Paused]   │ │
│  │    → Google Drive: Team Docs/                           │ │
│  │    Последняя конвертация: —                             │ │
│  └─────────────────────────────────────────────────────────┘ │
│                                                              │
│  Быстрая конвертация                                         │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │  Перетащите .md файл сюда или [Выбрать файл]           │ │
│  └─────────────────────────────────────────────────────────┘ │
│                                                              │
│  Последние конвертации                                       │
│  ┌──────────┬────────────────────┬──────────┬─────────────┐ │
│  │ Время    │ Файл               │ Статус   │ Ссылка      │ │
│  ├──────────┼────────────────────┼──────────┼─────────────┤ │
│  │ 14:30    │ longread.md         │ ✅ Done  │ [Открыть]   │ │
│  │ 13:15    │ summary.md          │ ✅ Done  │ [Открыть]   │ │
│  │ 12:00    │ report.md           │ ❌ Error │ [Детали]    │ │
│  └──────────┴────────────────────┴──────────┴─────────────┘ │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

### Страница настроек

```
┌──────────────────────────────────────────────────────────────┐
│  Settings                                      [← Назад]    │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  Google OAuth                                                │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │ Status: ✅ Connected (lel.roman@gmail.com)              │ │
│  │                          [Переподключить] [Отключить]   │ │
│  └─────────────────────────────────────────────────────────┘ │
│                                                              │
│  YAML Frontmatter                                            │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │ ○ Убрать при конвертации                                │ │
│  │ ● Конвертировать в шапку документа                      │ │
│  │ Поля для шапки: [title] [speaker] [date] [duration]     │ │
│  └─────────────────────────────────────────────────────────┘ │
│                                                              │
│  Стили                                                       │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │ Шрифт: [Google Sans      ▼]                             │ │
│  │ Каллауты: ● Простые таблицы  ○ Без каллаутов            │ │
│  └─────────────────────────────────────────────────────────┘ │
│                                                              │
│  Мониторинг                                                  │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │ Интервал проверки Google Drive: [5 мин ▼]               │ │
│  │ Реакция на: ● Новые файлы  ☑ Изменённые файлы          │ │
│  └─────────────────────────────────────────────────────────┘ │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

### Состояния

| Состояние | Описание |
|-----------|----------|
| Idle | Сервис запущен, мониторит папки, новых файлов нет |
| Converting | Обнаружен файл, идёт конвертация |
| Success | Конвертация завершена, ссылка на Google Doc доступна |
| Error | Ошибка конвертации (отображается в логах с деталями) |
| Paused | Мониторинг папки приостановлен пользователем |

---

## 5. API

### Health check

```
GET /health
```

```json
{
  "status": "ok",
  "version": "0.1.0",
  "watchedFolders": 2,
  "activeConversions": 0
}
```

### Ручная конвертация

```
POST /api/convert
Content-Type: multipart/form-data
```

```typescript
// Request: form-data с файлом + параметры
interface ConvertRequest {
  file: File;              // MD файл
  targetFolderId: string;  // ID папки на Google Drive
  documentName?: string;   // Имя Google Doc (по умолчанию — из title frontmatter или имя файла)
}

// Response
interface ConvertResponse {
  documentId: string;      // ID созданного Google Doc
  documentUrl: string;     // Ссылка на Google Doc
  title: string;           // Название документа
  convertedAt: string;     // ISO timestamp
}
```

### Управление watched folders

```
GET    /api/folders              — список отслеживаемых папок
POST   /api/folders              — добавить папку
PATCH  /api/folders/:id          — изменить настройки
DELETE /api/folders/:id          — удалить
POST   /api/folders/:id/pause    — приостановить мониторинг
POST   /api/folders/:id/resume   — возобновить мониторинг
```

```typescript
interface WatchedFolder {
  id: string;
  type: "local" | "gdrive";
  sourcePath: string;          // локальный путь или Google Drive folder ID
  targetFolderId: string;      // ID целевой папки на Google Drive
  filePattern: string;         // glob-паттерн (например "*.md" или "longread.md")
  status: "active" | "paused";
  lastChecked: string | null;
  createdAt: string;
}
```

### Логи конвертаций

```
GET /api/logs?limit=50&offset=0
```

```typescript
interface ConversionLog {
  id: string;
  sourceFile: string;
  sourceType: "local" | "gdrive" | "manual";
  documentId: string | null;
  documentUrl: string | null;
  status: "success" | "error";
  error: string | null;
  durationMs: number;
  convertedAt: string;
}
```

### Настройки

```
GET  /api/settings
PUT  /api/settings
```

```typescript
interface Settings {
  frontmatter: {
    mode: "strip" | "header";       // убрать или вставить в шапку
    headerFields: string[];          // поля для шапки: ["title", "speaker", "date"]
  };
  styles: {
    fontFamily: string;              // шрифт документа
    calloutsMode: "table" | "none";  // как отображать каллауты
  };
  monitoring: {
    gdrivePollingIntervalMin: number;  // интервал проверки Google Drive
    reactToUpdates: boolean;           // реагировать на изменения (не только новые)
  };
  google: {
    connected: boolean;
    email: string | null;
  };
}
```

---

## 6. Данные

### Хранилище

SQLite (файловая БД, без внешних зависимостей).

### Таблицы

```sql
-- Отслеживаемые папки
CREATE TABLE watched_folders (
  id TEXT PRIMARY KEY,
  type TEXT NOT NULL,           -- 'local' | 'gdrive'
  source_path TEXT NOT NULL,
  target_folder_id TEXT NOT NULL,
  file_pattern TEXT DEFAULT '*.md',
  status TEXT DEFAULT 'active',
  last_checked TIMESTAMP,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Логи конвертаций
CREATE TABLE conversion_logs (
  id TEXT PRIMARY KEY,
  source_file TEXT NOT NULL,
  source_type TEXT NOT NULL,    -- 'local' | 'gdrive' | 'manual'
  watched_folder_id TEXT,
  document_id TEXT,
  document_url TEXT,
  status TEXT NOT NULL,         -- 'success' | 'error'
  error TEXT,
  duration_ms INTEGER,
  converted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Настройки (key-value)
CREATE TABLE settings (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL
);

-- Обработанные файлы (дедупликация)
CREATE TABLE processed_files (
  file_path TEXT NOT NULL,
  file_hash TEXT NOT NULL,      -- MD5/SHA256 для определения изменений
  document_id TEXT,
  processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (file_path)
);
```

---

## 7. Ограничения

| Параметр | Лимит | Обоснование |
|----------|-------|-------------|
| Размер MD файла | 10 МБ | Ограничение Google Drive API на upload |
| Google Drive API | 300 запросов/мин | Rate limit Google API |
| Polling интервал (min) | 1 мин | Не перегружать Google API |
| Polling интервал (default) | 5 мин | Баланс скорости и ресурсов |
| Одновременных конвертаций | 3 | Не превышать rate limits |
| Длина имени документа | 255 символов | Ограничение Google Docs |
| Поддерживаемые MD элементы | Заголовки H1-H6, bold, italic, списки, таблицы, ссылки, код, каллауты | HTML-конвертация через Python markdown |
| НЕ поддерживается | Изображения, embedded файлы, dataview | Ограничение HTML → Google Doc конвертации |

---

## 8. План реализации

### Этап 1: Core (v0.1)

Минимальный работающий сервис.

- [ ] Структура проекта (FastAPI + SQLite + React)
- [ ] MD → HTML конвертер (Python-Markdown + расширения)
- [ ] Обработка каллаутов Obsidian → HTML таблицы
- [ ] Обработка YAML frontmatter (strip / header mode)
- [ ] Google Drive API: OAuth2 + upload HTML as Google Doc
- [ ] API endpoint: POST /api/convert (ручная конвертация)
- [ ] Базовый UI: форма загрузки файла + результат со ссылкой

### Этап 2: Мониторинг (v0.2)

Автоматическое отслеживание папок.

- [ ] Watchdog: мониторинг локальных папок
- [ ] Google Drive API: polling папок на изменения
- [ ] CRUD для watched folders (API + UI)
- [ ] Дедупликация: не конвертировать один файл дважды (hash check)
- [ ] Фоновый worker для конвертаций

### Этап 3: Admin Panel (v0.3)

Полноценная панель управления.

- [ ] UI: список watched folders с статусами
- [ ] UI: таблица логов конвертаций
- [ ] UI: страница настроек (frontmatter, стили, polling)
- [ ] UI: Google OAuth flow через браузер

### Этап 4: Стабилизация (v1.0)

- [ ] Docker-compose для деплоя (Traefik совместимый)
- [ ] Health check endpoint
- [ ] Graceful error handling и retry logic
- [ ] Документация

---

## 9. Тестирование

| Сценарий | Ожидаемый результат |
|----------|---------------------|
| Конвертация простого MD (заголовки, текст, списки) | Google Doc с сохранённым форматированием |
| MD с каллаутами `> [!tip]`, `> [!warning]` | Каллауты отображаются как таблицы с заголовками |
| MD с YAML frontmatter (mode: header) | Шапка документа с title, speaker, date |
| MD с YAML frontmatter (mode: strip) | Frontmatter не отображается в документе |
| MD с таблицами | Таблицы сохраняются в Google Doc |
| Мониторинг: новый файл в локальной папке | Автоконвертация в течение 10 секунд |
| Мониторинг: новый файл на Google Drive | Автоконвертация в течение polling интервала |
| Повторное появление того же файла (без изменений) | Пропуск (дедупликация по hash) |
| Изменённый файл (reactToUpdates: true) | Повторная конвертация, обновление Google Doc |
| Ошибка Google API (expired token) | Лог с ошибкой, уведомление в UI |
| Файл > 10 МБ | Отказ с понятным сообщением об ошибке |

---

## 10. Референсы

### Из текущего проекта (bz2-video-transcribe)

- `docs/reference/Obsidian-Export/obsidian_to_gdocs.py` — Python: парсинг каллаутов, тегов, внутренних ссылок. Regex-паттерны проверены на реальных документах
- `docs/reference/Obsidian-Export/obsidian-callouts.lua` — Lua: альтернативная реализация парсинга каллаутов (для Pandoc)
- `docs/reference/Obsidian → Google Docs/Obsidian → Google Docs.json` — n8n workflow: полный pipeline MD → HTML → Upload. Код в Code нодах содержит проверенную логику конвертации
- `docs/reference/Obsidian → Google Docs/topaz_nord_constants.js` — JS: структура каллаутов (13 типов + алиасы), helper-функции генерации HTML

### Технологии

- **Backend:** Python, FastAPI
- **Frontend:** React (Vite)
- **БД:** SQLite
- **MD → HTML:** Python-Markdown или mistune
- **File watcher:** watchdog (Python)
- **Google API:** google-api-python-client, google-auth
- **Deploy:** Docker, Traefik (рядом с bz2-video-transcriber)

### Google API

- Google Drive API: Files.create с mimeType conversion
- Google OAuth2: Service Account или OAuth2 для веб-приложений

---

## Открытые вопросы

- [ ] Service Account vs OAuth2 — для серверного приложения Service Account проще (не нужен refresh token flow), но ограничен одним аккаунтом. OAuth2 — гибче, но требует UI для авторизации
- [ ] Обновление существующего Google Doc vs создание нового — при изменении MD файла: обновлять тот же документ (сохраняет ссылку) или создавать новую версию?
- [ ] Нужна ли поддержка изображений — MD файлы из pipeline не содержат изображений, но универсальный инструмент может столкнуться с ними
- [ ] Стек frontend — React (как в transcriber) или что-то более лёгкое (Svelte, plain HTML)?

---

## История изменений

| Дата | Версия | Изменения |
|------|--------|-----------|
| 2026-02-23 | 1.0 | Первоначальная версия |

---

_Документ для планирования в Claude Code_
