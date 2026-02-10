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

## Определение типа по имени файла
- Regular events (ПШ): дата + тип в имени → `educational`
- Dated offsite с маркером `#` в имени → `leadership`
- Dated offsite без `#` → `educational`
- Offsite folder `Фамилия (Имя)` → `leadership`
- Offsite folder `Фамилия — Название` → `educational`
- ВСЕГДА использовать `config/events.yaml` для типов событий при парсинге

## Модели
- `VideoMetadata`: `content_type`, `event_category`, `event_name`, `is_offsite` (computed)
- `ContentType` и `EventCategory` — Enum из `app.models.schemas`

## Slides Integration
- Слайды опциональны — появляются если пользователь прикрепил файлы
- Поддерживаемые форматы: image/jpeg, image/png, application/pdf
- Извлечённый текст (markdown) передаётся в longread/story как контекст
- Лимиты: макс. 50 файлов, 10 MB на файл, 100 MB общий размер

## Archive Structure
- Выходные файлы сохраняются в `archive/{path}/pipeline_results.json`
- Кэш в `archive/{path}/.cache/` — версионированные промежуточные результаты
