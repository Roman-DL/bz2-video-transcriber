---
paths:
  - "backend/app/services/google/**"
---

# Rules: Google Drive API Client

## Авторизация
- ВСЕГДА Service Account (НЕ OAuth2)
- JSON-ключ: `config/service-account.json` — НИКОГДА не коммитить
- `google.oauth2.service_account.Credentials`
- Scope: `https://www.googleapis.com/auth/drive`

## 5 операций с API
1. `files().create()` — создание GDoc (mimeType: `application/vnd.google-apps.document`) — режим `once`
2. `files().update()` — обновление содержимого — режимы `one-way`, `two-way`
3. `files().export(mimeType='text/html')` — экспорт для обратной конвертации — `two-way`
4. `files().get(fields='modifiedTime')` — проверка изменений — `two-way`
5. `files().get(fields='id,name,mimeType')` — валидация папки при создании правила

## Upload
- HTML загрузка с `mimeType: text/html` → Google авто-конвертирует в Google Doc
- НЕ загружать как plain text или markdown напрямую

## Rate Limits
- 300 requests/min на проект
- 750 ГБ/день upload
- 10 МБ максимум для автоконвертации
- Max 3 concurrent операции в приложении

## Retry Strategy
- 429 (Rate limit) → exponential backoff: 1s, 4s, 16s
- 403 (Permission denied) → НЕ retry, логировать ошибку
- 404 (Not found) → удалить mapping из file_mappings
- 500/503 (Server error) → retry с backoff

## Проверка подключения
- `POST /api/settings/google/test` — тест Service Account credentials

## Документация
- Подробная архитектура: `docs/architecture/03-google-drive.md`
