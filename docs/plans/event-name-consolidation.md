# Консолидация event_name + единый формат файлов

## Контекст

1. **Дублирование `_get_stream_name`** в `saver.py:660` и `description_generator.py:199` — downstream резолвит display-имя мероприятия вместо parser.
2. **events.yaml устарел** — типы не соответствуют реальным мероприятиям.
3. **Старые offsite-форматы** (`Фамилия (Имя).mp4`, `2026.01 ФСТ. # Антоновы...`) — отдельная ветка парсинга с 4 regex и 5 функциями.
4. **Leadership только на offsite** — нужно поддержать и на regular-событиях.

**Цель:** Единый формат файлов, единый парсер, `event_name` заполняется всегда. Обратная совместимость НЕ нужна.

---

## Новый формат файлов

```
{дата} {тип}[.{поток}]. {тема} ({спикер}).ext
```

- Точка после типа — обязательный разделитель (поддерживает многословные типы)
- `"История"` в позиции темы → content_type=LEADERSHIP
- Тип мероприятия определяет regular/offsite через events.yaml lookup

**Примеры:**

| Файл | event_type | stream | title | content_type |
|------|-----------|--------|-------|-------------|
| `2025.04.07 ПШ.SV. Группа поддержки (Дмитрук).mp4` | ПШ | SV | Группа поддержки | educational |
| `2025.04.07 ПШ.SV. История (Антоновы Дмитрий и Юлия).mp4` | ПШ | SV | История | leadership |
| `2025.05.02 ШБМ. Тема (Спикер).mp4` | ШБМ | | Тема | educational |
| `2025.05.02 Форум TABTeam. История (Иванов Дмитрий).mp4` | Форум TABTeam | | История | leadership |
| `2025.04.07 МК.Бизнес. Тема (Спикер).mp4` | МК | Бизнес | Тема | educational |

---

## Шаг 1: Обновить `config/events.yaml`

Полная замена. Все типы (regular + offsite) с `display_name`:

```yaml
event_types:
  # --- Регулярные ---
  ПШ:
    name: "Понедельничная Школа"
    display_name: "ПШ"
    category: regular
    streams:
      SV: "Супервайзеры"
      НП: "Независимые партнёры"
  МК:
    name: "Мастер-класс"
    display_name: "МК"
    category: regular
    streams:
      Бизнес: "Мастер-класс по бизнесу"
      Продукт: "Мастер-класс по продукту"
  ВВК:
    name: "Встреча возможностей для клиентов"
    display_name: "ВВК"
    category: regular
    streams: {}
  ГР:
    name: "Группа роста"
    display_name: "ГР"
    category: regular
    streams: {}
  ГП:
    name: "Группа поддержки"
    display_name: "ГП"
    category: regular
    streams: {}
  Тема:
    name: "Тема"
    display_name: "Тема"
    category: regular
    streams: {}

  # --- Выездные ---
  ФСТ:
    name: "Февральский стартовый тренинг"
    display_name: "ФСТ"
    category: offsite
    streams: {}
  Форум TABTeam:
    name: "Форум TABTeam"
    display_name: "Форум TABTeam"
    category: offsite
    streams: {}
  Экстраваганза:
    name: "Экстраваганза"
    display_name: "Экстраваганза"
    category: offsite
    streams: {}
  ШБМ:
    name: "Школа будущих миллионеров"
    display_name: "ШБМ"
    category: offsite
    streams: {}
  ШБП:
    name: "Школа будущих президентов"
    display_name: "ШБП"
    category: offsite
    streams: {}
  Honors:
    name: "Honors"
    display_name: "Honors"
    category: offsite
    streams: {}
```

Удалить: `ВЫЕЗД` (виртуальный), `ФК`, `ВЕБ`, `ОБУ` (неактуальные), `date_format`, `filename_patterns`.

---

## Шаг 2: Новый regex и парсинг в parser.py

**Файл:** `backend/app/services/parser.py`

### 2a. Заменить `REGULAR_EVENT_PATTERN` на `EVENT_PATTERN`

```python
# Unified filename pattern (v0.69+)
# Format: {date} {type}[.{stream}]. {title} ({speaker}).ext
EVENT_PATTERN = re.compile(
    r'^(\d{4}\.\d{2}\.\d{2})\s+'   # Date: 2025.04.07
    r'(.+?)\.\s+'                    # Event group: ПШ.SV or Форум TABTeam
    r'(.+?)\s+'                      # Title: Группа поддержки or История
    r'\(([^)]+)\)'                   # Speaker/Names: (Светлана Дмитрук)
    r'(?:\.\w+)?$',                  # Extension: .mp4
    re.UNICODE
)
```

### 2b. Удалить старые regex (4 штуки)

- `OFFSITE_LEADERSHIP_PATTERN` (строки 56-61)
- `OFFSITE_EDUCATIONAL_PATTERN` (строки 66-72)
- `OFFSITE_FOLDER_PATTERN` (строки 77-82)
- `DATED_OFFSITE_PATTERN` (строки 88-96)

### 2c. Удалить старые функции парсинга offsite (5 штук)

- `parse_offsite_folder()` (~строка 217)
- `parse_dated_offsite_filename()` (~строка 261)
- `detect_content_type_from_filename()` — найти и удалить
- `_parse_dated_offsite_event()` (строка 427)
- `_parse_offsite_event()` (строка 481)

### 2d. Добавить `resolve_event_name()` (~строка 215)

```python
def resolve_event_name(event_type: str, stream: str) -> str:
    """Resolve short display name for an event.

    With stream: "{display_name}.{stream}" (e.g., "ПШ.SV")
    Without stream: display_name (e.g., "ВВК", "Форум TABTeam")
    Fallback: event_type code.
    """
    try:
        events_config = load_events_config()
        event_info = events_config.get("event_types", {}).get(event_type, {})
        display_name = event_info.get("display_name", event_type)
    except Exception:
        display_name = event_type

    if stream:
        return f"{display_name}.{stream}"
    return display_name
```

### 2e. Обновить `_parse_regular_event` → единый `_parse_event`

Парсинг event_group (группа 2 regex):
```python
event_group = match.group(2)  # "ПШ.SV" or "Форум TABTeam" or "МК.Бизнес"
if '.' in event_group:
    last_dot = event_group.rindex('.')
    event_type = event_group[:last_dot]
    stream = event_group[last_dot + 1:]
else:
    event_type = event_group
    stream = ""
```

Leadership detection:
```python
title = match.group(3)
if title == "История":
    content_type = ContentType.LEADERSHIP
else:
    content_type = ContentType.EDUCATIONAL
```

Archive path — уже обрабатывает оба категории (строки 391-410).

Добавить `event_name=resolve_event_name(event_type, stream)` в return.

### 2f. Упростить `parse_filename()`

Убрать параметр `event_name` (больше не нужен — event_name из filename). Убрать ветки dated_offsite и offsite. Оставить только `EVENT_PATTERN` + `_parse_event`.

---

## Шаг 3: `event_name` required в schemas.py

**Файл:** `backend/app/models/schemas.py` (строка 133)

```python
# Было:
event_name: str | None = None

# Стало:
event_name: str = ""  # Display name: "ПШ.SV", "Форум TABTeam", etc.
```

`str = ""` (не `str` without default) — для совместимости при ручном создании VideoMetadata в тестах.

---

## Шаг 4: Удалить `_get_stream_name` из saver.py

**Файл:** `backend/app/services/saver.py`

| Что | Строки | Действие |
|-----|--------|----------|
| `load_events_config` в import | 15 | Убрать |
| `self.events_config` в `__init__` | 69 | Удалить |
| Вызов `_get_stream_name` | 401-403 | → `stream_name = metadata.event_name` |
| Метод `_get_stream_name` | 660-692 | Удалить |

---

## Шаг 5: Удалить `_get_stream_name` из description_generator.py

**Файл:** `backend/app/services/description_generator.py`

| Что | Строки | Действие |
|-----|--------|----------|
| `load_events_config` в import | 11 | Убрать |
| `self.events_config` в `__init__` | 66 | Удалить |
| Вызов + переменная | 91-93 | Удалить 3 строки |
| `event_name=stream_name` | 105 | → `event_name=metadata.event_name` |
| Метод `_get_stream_name` | 199-228 | Удалить |

---

## Шаг 6: Упростить story_generator.py

**Файл:** `backend/app/services/story_generator.py`

Убрать fallback `or metadata.event_type`:

| Строка | Было | Стало |
|--------|------|-------|
| 116 | `metadata.event_name or metadata.event_type` | `metadata.event_name` |
| 208 | `metadata.event_name or metadata.event_type` | `metadata.event_name` |
| 276 | `metadata.event_name or metadata.event_type` | `metadata.event_name` |

---

## Шаг 7: Обновить тесты

### parser.py — полная переработка тестов

Старые тесты опирались на форматы `ПШ.SV Тема (Спикер)` и offsite-паттерны. Нужно переписать под новый формат `ТИП. Тема (Спикер)`.

**Ключевые test cases:**
- Regular с потоком: `2025.04.07 ПШ.SV. Группа поддержки (Дмитрук).mp4`
- Regular без потока: `2025.04.07 Тема. Название (Спикер).mp4`
- Leadership regular: `2025.04.07 ПШ.SV. История (Антоновы Дмитрий и Юлия).mp4`
- Leadership пара разные фамилии: `2025.04.07 ПШ.SV. История (Иванов Дмитрий и Петрова Юлия).mp4`
- Offsite educational: `2025.05.02 ШБМ. Тема (Спикер).mp4`
- Offsite leadership: `2025.05.02 ШБМ. История (Иванов Дмитрий).mp4`
- Multi-word event type: `2025.05.02 Форум TABTeam. Тема (Спикер).mp4`
- Stream с кириллицей: `2025.04.07 МК.Бизнес. Тема (Спикер).mp4`
- event_name: проверить resolve_event_name() для всех типов
- Invalid filename: ожидать FilenameParseError

### saver.py

- Тест 3 (get_stream_name): удалить
- Тест 4 (full save): добавить `event_name="ПШ.SV"` в mock

---

## Файлы для изменения

| Файл | Действие |
|------|----------|
| `config/events.yaml` | Полная замена — новые типы с display_name |
| `backend/app/services/parser.py` | Новый regex, удалить 4 regex + 5 функций offsite, resolve_event_name, "История" detection |
| `backend/app/models/schemas.py` | `event_name: str = ""` |
| `backend/app/services/saver.py` | Удалить `_get_stream_name`, events_config → `metadata.event_name` |
| `backend/app/services/description_generator.py` | Удалить `_get_stream_name`, events_config → `metadata.event_name` |
| `backend/app/services/story_generator.py` | Убрать fallback `or metadata.event_type` |

---

## Проверка

```bash
# Синтаксис
python3 -m py_compile backend/app/services/parser.py
python3 -m py_compile backend/app/services/saver.py
python3 -m py_compile backend/app/services/description_generator.py
python3 -m py_compile backend/app/services/story_generator.py

# Встроенные тесты
python3 backend/app/services/parser.py
python3 backend/app/services/saver.py
```
