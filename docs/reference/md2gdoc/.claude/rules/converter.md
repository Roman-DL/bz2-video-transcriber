---
paths:
  - "backend/app/services/converter/**"
---

# Rules: Converter (MD↔HTML↔GDoc)

## Прямая конвертация (MD → GDoc)
1. Parse frontmatter (режим `strip` или `header`)
2. Convert MD → HTML (Python-Markdown / mistune)
3. Image Resolution (MVP: skip + placeholder + warning)
4. Upload HTML → Google Drive с `mimeType: application/vnd.google-apps.document` (авто-конвертация)

## Обратная конвертация (GDoc → MD, two-way)
1. Export как HTML (`Files.export`)
2. Detect callouts (таблица 2×1 + shading + emoji)
3. Restore image links (сопоставление с file_mappings)
4. Convert HTML → MD

## ВСЕГДА поддерживать оба направления конвертации в модуле

## Каллауты
- Формат GDoc: HTML таблица 2 строки × 1 колонка, первая строка — цветной фон + emoji
- 8 типов: info, tip, warning, danger, example, question, abstract, quote
- Маппинг emoji → тип → цвет фона (детали в `docs/architecture/01-converter.md`)
- Обратная конвертация: detect таблицу + shading + emoji → восстановить `> [!type]`

## Frontmatter
- `strip` — удалить перед конвертацией (default)
- `header` — вставить как шапку документа с выбранными полями
- При обратной конвертации — сохранять если был

## Изображения (MVP)
- Локальные изображения → placeholder `[Image: filename]` + warning в conversion_log
- Внешние URL → работают (HTML `<img src="...">`)
- НЕ загружать изображения на Google Drive в MVP
- Будущее: `ImageResolver` для загрузки в `_images/` подпапку

## Поддерживаемые элементы
- H1-H6, bold, italic, strikethrough
- Упорядоченные и неупорядоченные списки
- Таблицы, ссылки
- Inline и block code
- Callouts (8 типов)

## Документация
- Подробная архитектура: `docs/architecture/01-converter.md`
- Референсный код: `docs/reference/` (obsidian_to_gdocs.py, topaz_nord_constants.js)
