---
doc_type: reference
status: active
updated: 2026-02-21
audience: [developer, ai-agent]
tags:
  - pipeline
  - stage
---

# Этап 1: Parse Filename

[Обзор Pipeline](README.md) | [Далее: Transcribe >](02-transcribe.md)

---

## Назначение

Извлечение метаданных из имени медиафайла по установленному паттерну. Автоматическое определение типа контента (`ContentType`) и категории события (`EventCategory`).

> **Примечание:** Этап детерминистический — LLM не используется, промптов нет.

## Input / Output

| Направление | Тип | Описание |
|-------------|-----|----------|
| **Input** | `video_path: Path` | Путь к медиафайлу (из `context.metadata`) |
| **Output** | `VideoMetadata` | Pydantic-модель с метаданными |

### Поля VideoMetadata

| Поле | Тип | Описание |
|------|-----|----------|
| `date` | `date` | Дата события |
| `event_type` | `str` | Тип мероприятия (ПШ, ГП, и т.д.) |
| `stream` | `str` | Часть/поток (SV, MV, и т.д.) |
| `title` | `str` | Название темы |
| `speaker` | `str` | Спикер |
| `original_filename` | `str` | Исходное имя файла |
| `video_id` | `str` | Уникальный идентификатор |
| `source_path` | `Path` | Путь к исходному файлу |
| `archive_path` | `Path` | Путь в архиве |
| `duration_seconds` | `float \| None` | Длительность в секундах |
| `content_type` | `ContentType` | Тип контента (EDUCATIONAL/LEADERSHIP) |
| `event_category` | `EventCategory` | Категория события (REGULAR/OFFSITE) |
| `event_name` | `str` | Display name события (всегда заполнен, v0.69+): `"ПШ.SV"`, `"Форум TABTeam"` |
| `stream_full` | computed | Полный идентификатор: `{event_type}.{stream}` |
| `is_offsite` | computed | `True` если `event_category == OFFSITE` |

## Категории событий (v0.21+)

События делятся на две категории:

| Категория | EventCategory | Источник | Пример |
|-----------|---------------|----------|--------|
| Регулярные | `REGULAR` | Еженедельные школы | ПШ, ГП, ФК |
| Выездные | `OFFSITE` | Выездные мероприятия | Лидерство, Обучение |

## Типы контента (v0.69+)

Контент автоматически классифицируется по теме в имени файла:

| Тип | ContentType | Правило | Пример |
|-----|-------------|---------|--------|
| Образовательный | `EDUCATIONAL` | Тема не начинается с `#История` | `2025.04.07 ПШ.SV. Группа поддержки (Светлана Дмитрук).mp4` |
| Лидерство | `LEADERSHIP` | Тема начинается с `#История` (маркер `#` убирается парсером) | `2025.04.07 ПШ.SV. #История (Антоновы Дмитрий и Юлия).mp4` |

## Паттерн имени файла (v0.69+)

Единый формат для всех типов событий (regular и offsite):

```
{дата} {тип}[.{поток}]. {тема} ({спикер}).{ext}
```

**Примеры:**
- `2025.04.07 ПШ.SV. Группа поддержки (Светлана Дмитрук).mp4` — regular с потоком
- `2025.05.02 ШБМ. Тема (Спикер).mp4` — offsite без потока
- `2025.05.02 Форум TABTeam. #История (Иванов Дмитрий).mp4` — offsite, leadership
- `2025.04.07 МК.Бизнес. Тема (Спикер).mp4` — regular с кириллическим потоком

**Ключевые правила:**
- Точка после типа/потока обязательна: `ПШ.SV.` (не `ПШ.SV `)
- Тема начинается с `#История` → `content_type=LEADERSHIP` (маркер `#` убирается парсером, в `title` попадает `"История"` или `"История семьи"` и т.д.)
- Тип события определяет `event_category` через `events.yaml`
- `event_name` заполняется через `resolve_event_name()`: `"ПШ.SV"`, `"Форум TABTeam"`

**Поддерживаемые форматы:** `.mp4`, `.mkv`, `.mp3`, `.wav`, `.m4a`, `.md` и другие медиафайлы.

## Структура архива

### Регулярные события (`event_category=REGULAR`)

```
archive/
  {год}/
    {тип}/
      {MM.DD поток. тема (спикер)}/
          video.mp4
          transcript_raw.txt
          transcript_chunks.json
          longread.md / story.md
          summary.md
          pipeline_results.json
```

**Пример:** `archive/2025/ПШ/04.07 SV. Группа поддержки (Светлана Дмитрук)/`

### Выездные события (`event_category=OFFSITE`)

```
archive/
  {год}/
    {MM event_type}/
      {тема} ({спикер})/
          video.mp4
          ...
```

**Пример:** `archive/2025/05 Форум TABTeam/История (Иванов Дмитрий)/`

**Почему такая структура:**
- Год на верхнем уровне — удобная навигация по времени
- Группировка по типу события (ПШ, ГП) для регулярных
- Дата и поток в имени конечной папки для регулярных событий — 3 уровня вместо 4
- `{MM event_type}` для выездных — логическая группировка материалов одного мероприятия с сортировкой по месяцу

## Генерация video_id

Уникальный идентификатор видео формируется как:

```
{дата}_{мероприятие}[-{часть}]_{slug-темы}
```

**Примеры:**
- `2025-04-07_ПШ-SV_группа-поддержки` — с частью
- `2025-04-07_ПШ_группа-поддержки` — без части

Slug сохраняет кириллицу в lowercase.

## Валидация

Типы мероприятий и их части валидируются по конфигу `config/events.yaml`.
При неизвестном типе/части выводится warning, но обработка продолжается.

## Определение длительности

После парсинга имени файла этап определяет длительность медиа:

1. **Основной способ:** `ffprobe` через `get_media_duration()`
2. **Fallback:** Оценка по размеру файла через `estimate_duration_from_size()` (разные битрейты для аудио/видео)

Результат записывается в `duration_seconds`.

## Error Handling

При несоответствии имени файла паттерну выбрасывается `FilenameParseError` с понятным сообщением об ожидаемом формате.

## Тестирование

```bash
cd backend
source .venv/bin/activate  # macOS требует venv
python -m app.services.parser
```

**Тесты покрывают (17 тестов):**
- Парсинг единого формата (с потоком и без)
- Leadership по маркеру `#История` (одиночный и множественные спикеры)
- Offsite события (ШБМ, Форум TABTeam)
- Мастер-класс с кириллическим потоком (МК.Бизнес)
- Генерация video_id и archive_path
- `resolve_event_name()` — display name событий
- MD файлы (транскрипты MacWhisper)

---

## Связанные документы

- **Stage:** [`backend/app/services/stages/parse_stage.py`](../../backend/app/services/stages/parse_stage.py)
- **Сервис парсинга:** [`backend/app/services/parser.py`](../../backend/app/services/parser.py)
- **Модели:** [`backend/app/models/schemas.py`](../../backend/app/models/schemas.py) — `VideoMetadata`, `ContentType`, `EventCategory`
- **Утилиты:** [`backend/app/utils/media_utils.py`](../../backend/app/utils/media_utils.py) — `get_media_duration()`, `estimate_duration_from_size()`
- **Типы мероприятий:** [`config/events.yaml`](../../config/events.yaml)
