# API Reference

HTTP API endpoints md2gdoc. Все response-модели — Pydantic `CamelCaseModel` (Python `snake_case` → JSON `camelCase`).

## Rules

### `GET /api/rules`

Список всех правил.

**Response:** `RuleListResponse`
```json
{
  "rules": [
    {
      "id": 1,
      "name": "Obsidian Notes",
      "sourcePath": "/mnt/source/notes",
      "targetFolderId": "1abc...",
      "mode": "one-way",
      "filePattern": "*.md",
      "recursive": false,
      "pollingIntervalMin": 5,
      "status": "active",
      "lastChecked": "2026-02-23T10:00:00Z"
    }
  ]
}
```

### `POST /api/rules`

Создать новое правило.

**Request:** `RuleCreateRequest`
```json
{
  "name": "Obsidian Notes",
  "sourcePath": "/mnt/source/notes",
  "targetFolderId": "1abc...",
  "mode": "one-way",
  "filePattern": "*.md",
  "recursive": false,
  "pollingIntervalMin": 5
}
```

### `PATCH /api/rules/:id`

Обновить правило. Partial update — только переданные поля.

### `DELETE /api/rules/:id`

Удалить правило и связанные file_mappings.

---

## Rule Actions

### `POST /api/rules/:id/pause`

Приостановить мониторинг правила (status → `paused`).

### `POST /api/rules/:id/resume`

Возобновить мониторинг (status → `active`).

### `POST /api/rules/:id/trigger`

Принудительно запустить сканирование и конвертацию (не ждать polling interval).

---

## Quick Convert

### `POST /api/convert`

Разовая конвертация одного файла без создания правила.

**Request:**
```json
{
  "sourcePath": "/mnt/source/notes/readme.md",
  "targetFolderId": "1abc..."
}
```

**Response:** `ConvertResponse`
```json
{
  "documentId": "1xyz...",
  "documentUrl": "https://docs.google.com/document/d/1xyz.../edit",
  "conversionTimeMs": 1250
}
```

---

## Logs

### `GET /api/logs`

Лог конвертаций с фильтрацией.

**Query params:**
- `ruleId` — фильтр по правилу
- `status` — `success` | `error`
- `limit` — количество записей (default: 50)
- `offset` — пагинация

**Response:** `LogListResponse`
```json
{
  "logs": [
    {
      "id": 1,
      "ruleId": 1,
      "sourcePath": "/mnt/source/notes/readme.md",
      "documentId": "1xyz...",
      "status": "success",
      "conversionTimeMs": 1250,
      "createdAt": "2026-02-23T10:05:00Z"
    }
  ],
  "total": 42
}
```

---

## Settings

### `GET /api/settings`

Текущие настройки приложения.

### `PUT /api/settings`

Обновить настройки.

### `POST /api/settings/google/test`

Проверить подключение Google Drive (валидация Service Account credentials).

**Response:**
```json
{
  "connected": true,
  "email": "md2gdoc@project.iam.gserviceaccount.com"
}
```

---

## Health

### `GET /health`

Health check endpoint.

**Response:**
```json
{
  "status": "ok",
  "version": "0.0.0",
  "googleConnected": true,
  "activeRules": 0
}
```

---

## Подробнее

- Rules Engine архитектура: [architecture/02-rules-engine.md](architecture/02-rules-engine.md)
- Google Drive API детали: [architecture/03-google-drive.md](architecture/03-google-drive.md)
- Pydantic CamelCaseModel: `.claude/rules/api.md`
