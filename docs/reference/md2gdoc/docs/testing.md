# Тестирование

Стратегия тестирования md2gdoc.

## Настройка окружения

### macOS

На macOS нельзя устанавливать пакеты в системный Python. Используй виртуальное окружение:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Проверка синтаксиса без запуска

```bash
python3 -m py_compile backend/app/services/converter/md_to_html.py
python3 -m py_compile backend/app/models/schemas.py
```

---

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
├── e2e/
│   └── test_full_flow.py       # Правило → мониторинг → конвертация → GDoc
└── fixtures/
    ├── sample.md               # MD с разным форматированием
    ├── callouts.md             # Все 8 типов callouts
    ├── frontmatter.md          # YAML frontmatter
    └── google_api/             # Mock JSON-ответы Google API
        ├── file_create.json
        ├── file_update.json
        └── file_export.json
```

---

## Unit Tests

### Converter — что тестировать

| Тест | Входные данные | Ожидание |
|------|---------------|----------|
| Заголовки H1-H6 | `# Title` … `###### H6` | Корректные `<h1>`…`<h6>` теги |
| Списки (nested) | `- item\n  - sub` | Вложенные `<ul><li>` |
| Таблицы | MD таблица 3×3 | `<table>` с thead/tbody |
| Код (inline + block) | `` `code` `` + fenced | `<code>` + `<pre><code>` |
| Ссылки + bold/italic | `[text](url)` + `**b**` + `*i*` | `<a>`, `<b>`, `<i>` |

### Callouts — 8 типов

```python
@pytest.mark.parametrize("callout_type,icon,color", [
    ("info", "ℹ️", "#D1ECF1"),
    ("tip", "💡", "#D4EDDA"),
    ("warning", "⚠️", "#FFF3CD"),
    ("danger", "❌", "#F8D7DA"),
    ("example", "📝", "#E2E3E5"),
    ("question", "❓", "#CCE5FF"),
    ("abstract", "📌", "#E2E3E5"),
    ("quote", "💬", "#E2E3E5"),
])
def test_callout_to_html(callout_type, icon, color):
    md = f'> [!{callout_type}] Title\n> Content'
    html = convert_md_to_html(md)
    assert icon in html
    assert color in html
    assert "<table" in html  # Таблица 2×1
```

### Callout Round-trip (MD → HTML → MD)

Критично для `two-way` режима:
- Каллаут → HTML таблица → обратно каллаут
- Сохранение типа, заголовка, форматирования внутри

### Frontmatter

| Режим | Вход | Выход |
|-------|------|-------|
| `strip` | `---\ntitle: X\n---\nBody` | `Body` (frontmatter удалён) |
| `header` | `---\ntitle: X\nspeaker: Y\n---\nBody` | Шапка с полями + `Body` |

### Rules Engine — 3 режима

```python
def test_rule_default_recursive():
    """once → recursive=True, one-way/two-way → recursive=False."""
    rule_once = create_rule(mode="once")
    assert rule_once.recursive is True

    rule_oneway = create_rule(mode="one-way")
    assert rule_oneway.recursive is False
```

### Change Detection

| Режим | Условие | Действие |
|-------|---------|----------|
| `once` | Файл не в `file_mappings` | Конвертировать |
| `once` | Файл уже в `file_mappings` | Пропустить |
| `one-way` | SHA-256 hash изменился | Обновить GDoc |
| `one-way` | Hash не изменился | Пропустить |
| `two-way` | Source `modified_at` > target | MD → GDoc |
| `two-way` | Target `modified_at` > source | GDoc → MD |

---

## Integration Tests

### Google Drive API

Требуется реальный Service Account + тестовая папка на Google Drive.

**Сценарии:**
- Создание документа (upload HTML → GDoc)
- Обновление содержимого существующего документа
- Export (GDoc → HTML) для обратной конвертации
- Проверка `modifiedTime` для change detection
- Error handling: 403 (нет доступа), 404 (удалён), 429 (rate limit)

### Mock Google API (для локальной разработки)

```python
from unittest.mock import patch, MagicMock

@patch("googleapiclient.discovery.build")
def test_upload_document(mock_build):
    mock_service = MagicMock()
    mock_build.return_value = mock_service
    mock_service.files().create().execute.return_value = {
        "id": "test_doc_id",
        "webViewLink": "https://docs.google.com/document/d/test_doc_id/edit"
    }

    client = GoogleDriveClient(service_account_path="fake.json")
    result = client.upload_html("<h1>Test</h1>", folder_id="folder123")
    assert result["id"] == "test_doc_id"
```

### Sync Manager

- Scanning директории (mock filesystem через `tmp_path`)
- Polling loop с интервалом (mock timer)
- Очередь конвертации (max 3 concurrent — проверить семафор)

### FastAPI Endpoints

```python
from fastapi.testclient import TestClient

def test_create_rule(client: TestClient):
    response = client.post("/api/rules", json={
        "name": "Test Rule",
        "sourcePath": "/tmp/test",
        "targetFolderId": "folder123",
        "mode": "once",
        "filePattern": "*.md"
    })
    assert response.status_code == 201
    assert response.json()["name"] == "Test Rule"
```

---

## E2E Tests

Полный цикл (требуется реальный Google API):

1. Создать правило через `POST /api/rules`
2. Положить MD файл в source directory
3. Дождаться polling cycle (или `POST /api/rules/:id/trigger`)
4. Проверить что Google Doc создан
5. Проверить содержимое (callouts, таблицы, форматирование)

---

## Запуск

```bash
cd backend
source .venv/bin/activate

# Все unit тесты
pytest tests/unit/

# Конкретный модуль
pytest tests/unit/test_converter.py -v

# Только callouts
pytest tests/unit/test_callouts.py -v

# Integration (нужен Service Account)
pytest tests/integration/ --google-sa=config/service-account.json

# С coverage
pytest tests/unit/ --cov=app --cov-report=term-missing
```

---

## Связанные документы

- [configuration.md](configuration.md) — переменные окружения
- [deployment.md](deployment.md) — деплой и Docker
- [architecture/01-converter.md](architecture/01-converter.md) — детали конвертера
- [architecture/02-rules-engine.md](architecture/02-rules-engine.md) — Rules Engine
