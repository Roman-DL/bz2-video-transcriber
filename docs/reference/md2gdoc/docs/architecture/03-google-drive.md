# 03 — Google Drive Integration

Интеграция с Google Drive API: авторизация через Service Account, загрузка и обновление документов, экспорт для обратной конвертации.

**Обзор архитектуры:** [ARCHITECTURE.md](../ARCHITECTURE.md)

---

## Обзор

```
┌─────────────────────┐          ┌──────────────────────────────────┐
│   md2gdoc Service   │          │         Google Drive              │
│                     │          │                                  │
│  ┌───────────────┐  │  API     │  ┌──────────────────────────┐   │
│  │ Google Drive  │──┼─────────▶│  │ Shared Folder            │   │
│  │ Client        │  │          │  │ (shared с Service Acc.)  │   │
│  │               │◀─┼──────────│  │  ├── doc1.gdoc           │   │
│  │ - create      │  │          │  │  ├── doc2.gdoc           │   │
│  │ - update      │  │          │  │  └── _images/ (будущее)  │   │
│  │ - export      │  │          │  └──────────────────────────┘   │
│  └───────┬───────┘  │          │                                  │
│          │          │          └──────────────────────────────────┘
│  ┌───────┴───────┐  │
│  │ Service Acc.  │  │
│  │ JSON key      │  │
│  └───────────────┘  │
└─────────────────────┘
```

---

## Авторизация: Service Account

### Что это

Google Service Account — сервисный аккаунт для автономной авторизации без участия пользователя. Идентифицируется JSON-ключом и email-адресом.

### Настройка

1. Создать Service Account в Google Cloud Console
2. Скачать JSON-ключ
3. Загрузить ключ в md2gdoc (через admin panel или поместить в `/config/service-account.json`)
4. Расшарить целевую папку на Google Drive на email Service Account (одноразовая операция)

### Авторизация в коде

```python
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/drive']

credentials = Credentials.from_service_account_file(
    'config/service-account.json',
    scopes=SCOPES
)
drive_service = build('drive', 'v3', credentials=credentials)
```

### Преимущества

- Токен не протухает (в отличие от OAuth2 refresh tokens)
- Не нужен UI для авторизации
- Работает автономно 24/7

---

## Операции с Google Drive API

### 1. Создание документа (режим `once`)

Загрузка HTML с автоконвертацией в Google Doc:

```python
from googleapiclient.http import MediaInMemoryUpload

html_content = convert_md_to_html(md_file)

media = MediaInMemoryUpload(
    html_content.encode('utf-8'),
    mimetype='text/html'
)

file_metadata = {
    'name': 'Document Title',
    'parents': [target_folder_id],
    'mimeType': 'application/vnd.google-apps.document'  # автоконвертация
}

result = drive_service.files().create(
    body=file_metadata,
    media_body=media,
    fields='id, webViewLink'
).execute()

# result['id'] → Google Doc ID
# result['webViewLink'] → ссылка для просмотра
```

> `mimeType: application/vnd.google-apps.document` — ключ к бесплатной автоконвертации. Google Drive сам конвертирует загруженный HTML в нативный Google Doc.

### 2. Обновление документа (режимы `one-way`, `two-way`)

Замена содержимого существующего документа (ссылка сохраняется):

```python
media = MediaInMemoryUpload(
    new_html_content.encode('utf-8'),
    mimetype='text/html'
)

drive_service.files().update(
    fileId=document_id,
    media_body=media
).execute()
```

### 3. Экспорт документа (режим `two-way`)

Получение содержимого Google Doc для обратной конвертации:

```python
content = drive_service.files().export(
    fileId=document_id,
    mimeType='text/html'
).execute()

# content — HTML-строка для обратного парсинга в MD
```

### 4. Проверка изменений (режим `two-way`)

Получение `modifiedTime` для определения изменений:

```python
file = drive_service.files().get(
    fileId=document_id,
    fields='modifiedTime'
).execute()

# file['modifiedTime'] → ISO 8601 timestamp
```

### 5. Получение информации о папке

Для валидации при создании правила:

```python
folder = drive_service.files().get(
    fileId=folder_id,
    fields='id, name, mimeType'
).execute()

# Проверить: mimeType == 'application/vnd.google-apps.folder'
# Проверить: Service Account имеет доступ (иначе 404)
```

---

## Rate Limits и Retry

### Лимиты Google Drive API

| Параметр | Лимит |
|----------|-------|
| Запросы | 300 / мин (на Service Account) |
| Upload | 750 ГБ / день |
| Размер файла | 10 МБ для автоконвертации |

### Стратегия

- Максимум **3 одновременных конвертации** (queue в Sync Manager)
- **Exponential backoff** при 429 (Rate Limit):
  - 1-я попытка: +1 сек
  - 2-я попытка: +4 сек
  - 3-я попытка: +16 сек
  - Далее: ошибка в лог, retry при следующем polling
- **403 (Forbidden)** — ошибка доступа, не retry. Логировать, пометить правило как проблемное

### Обработка ошибок

| Код | Причина | Действие |
|-----|---------|----------|
| 200 | OK | Записать в file_mappings |
| 403 | Нет доступа к папке | Лог ошибки, не retry |
| 404 | Документ/папка удалена | Лог, удалить mapping |
| 429 | Rate limit | Exponential backoff |
| 500/503 | Ошибка Google | Retry (3 попытки) |

---

## Настройки Service Account в UI

```typescript
interface GoogleSettings {
  serviceAccountEmail: string | null;  // email из JSON-ключа
  keyFilePath: string;                 // путь к JSON-ключу на сервере
  configured: boolean;                 // ключ загружен и валиден
}
```

### Проверка подключения

Endpoint `POST /api/settings/google/test`:
1. Загрузить credentials из JSON-ключа
2. Выполнить `drive_service.files().list(pageSize=1)`
3. Если успешно — `configured: true`
4. Если ошибка — вернуть описание проблемы

---

## Будущее: загрузка изображений

Когда Image Resolution будет реализована:

1. Локальные изображения загружаются в подпапку `_images/` рядом с документом
2. Делаются публично доступными (или доступными по ссылке)
3. URL подставляется в HTML перед созданием Google Doc
4. Mapping изображений хранится для обратной конвертации

```python
# Загрузка изображения
image_metadata = {
    'name': 'photo.png',
    'parents': [images_folder_id]
}
media = MediaFileUpload('path/to/photo.png', mimetype='image/png')
image_file = drive_service.files().create(
    body=image_metadata,
    media_body=media,
    fields='id, webContentLink'
).execute()

# Публичный доступ по ссылке
drive_service.permissions().create(
    fileId=image_file['id'],
    body={'type': 'anyone', 'role': 'reader'}
).execute()
```

---

_Обновлять при изменении интеграции с Google Drive._
