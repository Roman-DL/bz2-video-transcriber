---
paths:
  - "backend/app/services/parser.py"
  - "backend/app/services/saver.py"
  - "**/*longread*"
  - "**/*story*"
  - "config/events.yaml"
---

# Rules: Content Types & Archive

## Content Types
- `educational` → `{title} ({speaker}) — лонгрид.md` + `{title} ({speaker}) — саммари.md` (обучающие темы)
- `leadership` → `{title} ({speaker}) — история.md` (лидерские истории, 8 блоков)
- Имена MD-файлов формируются из `VideoMetadata.title` + `abbreviate_name(speaker)` через `_build_md_filename()`
- Тип определяется по имени файла при парсинге — см. правила ниже

## Event Categories
- `regular`: `archive/{year}/{event_type}/{MM.DD stream. title (speaker)}/`
- `offsite`: `archive/{year}/{MM event_type}/{title (speaker)}/`

## Определение типа по имени файла (v0.69+, день опционален с v0.71)
- Единый формат: `{ГГГГ.ММ[.ДД]} {тип}[.{поток}]. {тема} ({спикер}).ext`
- День опционален — при отсутствии `day=1` (удобно для выездных мероприятий)
- Тема начинается с `#История` → `content_type=LEADERSHIP` (маркер `#` убирается парсером, на любом типе события)
- Иначе → `content_type=EDUCATIONAL`
- `event_category` определяется через `events.yaml` → поле `category` у типа события
- ВСЕГДА использовать `config/events.yaml` для типов событий при парсинге

## Модели
- `VideoMetadata`: `content_type`, `event_category`, `event_name: str` (всегда заполнен, v0.69+), `is_offsite` (computed)
- `ContentType` и `EventCategory` — Enum из `app.models.schemas`
- `event_name` — display name из `resolve_event_name()`: `"ПШ.SV"`, `"Форум TABTeam"` и т.д.

## Multi-Speaker Scenarios (v0.79+, ADR-022)
- Сценарий определяется программно по `SpeakerInfo.scenario` (из `parse_speakers()`)
- `single` / `None` → стандартный pipeline без изменений
- `co_speakers` → единый текст, атрибуция идей, оба спикера в шапке чанка
- `lineup` → H2-разделы по участникам `## Тема (Фамилия Имя)`, per-chunk шапки
- `qa` → раздел «Вопросы и ответы», SpeakerN убирается промптом
- Комбинации: `co_speakers_qa`, `lineup_qa`
- **Lineup → educational** (longread + summary). Story видит только co_speakers
- Промпты: условные секции «Мультиспикерный контент» в конце `instructions.md`
- Контекст сценария — в user prompt через `build_speaker_context()`, НЕ хардкод в промпте

## Slides Integration
- Слайды опциональны — появляются если пользователь прикрепил файлы
- Поддерживаемые форматы: image/jpeg, image/png, application/pdf
- Извлечённый текст (markdown) передаётся в longread/story как контекст
- Лимиты: макс. 50 файлов, 10 MB на файл, 100 MB общий размер

## Archive Structure
- Выходные файлы сохраняются в `archive/{path}/pipeline_results.json`
- Кэш в `archive/{path}/.cache/` — версионированные промежуточные результаты
