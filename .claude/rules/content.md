---
globs: backend/app/services/parser.py,backend/app/services/saver.py,*longread*,*story*,config/events.yaml
---

# Rules: Content Types & Archive

## Content Types
- `educational` → `longread.md` + `summary.md` (обучающие темы)
- `leadership` → `story.md` (лидерские истории, 8 блоков)
- Тип определяется по имени файла при парсинге — см. правила ниже

## Event Categories
- `regular`: `archive/{year}/{event_type}/{MM.DD}/{Title}/`
- `offsite`: `archive/{year}/Выездные/{event_name}/{Title}/`

## Определение типа по имени файла (v0.69+, день опционален с v0.71)
- Единый формат: `{ГГГГ.ММ[.ДД]} {тип}[.{поток}]. {тема} ({спикер}).ext`
- День опционален — при отсутствии `day=1` (удобно для выездных мероприятий)
- Тема = `"История"` → `content_type=LEADERSHIP` (на любом типе события)
- Иначе → `content_type=EDUCATIONAL`
- `event_category` определяется через `events.yaml` → поле `category` у типа события
- ВСЕГДА использовать `config/events.yaml` для типов событий при парсинге

## Модели
- `VideoMetadata`: `content_type`, `event_category`, `event_name: str` (всегда заполнен, v0.69+), `is_offsite` (computed)
- `ContentType` и `EventCategory` — Enum из `app.models.schemas`
- `event_name` — display name из `resolve_event_name()`: `"ПШ.SV"`, `"Форум TABTeam"` и т.д.

## Slides Integration
- Слайды опциональны — появляются если пользователь прикрепил файлы
- Поддерживаемые форматы: image/jpeg, image/png, application/pdf
- Извлечённый текст (markdown) передаётся в longread/story как контекст
- Лимиты: макс. 50 файлов, 10 MB на файл, 100 MB общий размер

## Archive Structure
- Выходные файлы сохраняются в `archive/{path}/pipeline_results.json`
- Кэш в `archive/{path}/.cache/` — версионированные промежуточные результаты
