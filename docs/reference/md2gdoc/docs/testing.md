# Тестирование

Стратегия тестирования md2gdoc.

## Структура тестов

```
backend/tests/
├── unit/
│   ├── test_converter.py       # MD↔HTML↔GDoc маппинг
│   ├── test_rules.py           # Rules CRUD, валидация
│   ├── test_change_detection.py # SHA-256 hash, change detection
│   └── test_callouts.py        # Callout конвертация (8 типов)
├── integration/
│   ├── test_google_drive.py    # Google Drive API (реальный Service Account)
│   ├── test_sync_manager.py    # Polling loop, file scanning
│   └── test_api.py             # FastAPI endpoints
└── e2e/
    └── test_full_flow.py       # Правило → мониторинг → конвертация → GDoc
```

## Unit Tests

### Converter
- MD → HTML: каждый поддерживаемый элемент (H1-H6, списки, таблицы, код, ссылки)
- Callouts: 8 типов (info, tip, warning, danger, example, question, abstract, quote)
- Callout round-trip: MD → HTML table → MD (обратная конвертация)
- Frontmatter: strip mode, header mode
- Изображения: локальные → placeholder, внешние URL → без изменений

### Rules Engine
- CRUD операции: создание, чтение, обновление, удаление правил
- Валидация: обязательные поля, допустимые значения mode
- Default recursive: `true` для `once`, `false` для `one-way`/`two-way`

### Change Detection
- SHA-256 хеширование содержимого файла
- `once`: файл не в file_mappings → новый
- `one-way`: hash изменился → обновить
- `two-way`: сравнение timestamps

## Integration Tests

### Google Drive API
- Требуется реальный Service Account (тестовая папка на Google Drive)
- Создание документа (upload HTML → GDoc)
- Обновление содержимого
- Export (GDoc → HTML)
- Проверка modifiedTime
- Error handling: 403, 404, 429

### Sync Manager
- Scanning директории (mock filesystem)
- Polling loop с интервалом
- Очередь конвертации (max 3 concurrent)

## E2E Tests

Полный цикл:
1. Создать правило через API
2. Положить MD файл в source directory
3. Дождаться polling cycle
4. Проверить что Google Doc создан
5. Проверить содержимое (callouts, таблицы, форматирование)

## Локальная разработка

### Mock Google API

Для разработки без реального Service Account:
- Mock `googleapiclient.discovery.build()` через `unittest.mock`
- Тестовые JSON-ответы в `backend/tests/fixtures/`

### Тестовые файлы

- `backend/tests/fixtures/sample.md` — MD с разным форматированием
- `backend/tests/fixtures/callouts.md` — все 8 типов callouts
- `backend/tests/fixtures/frontmatter.md` — YAML frontmatter

## Запуск

```bash
# Все unit тесты
cd backend && pytest tests/unit/

# Integration (нужен Service Account)
cd backend && pytest tests/integration/ --google-sa=config/service-account.json

# Конкретный модуль
cd backend && pytest tests/unit/test_converter.py -v
```
