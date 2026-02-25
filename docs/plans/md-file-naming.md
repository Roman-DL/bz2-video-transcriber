# План: осмысленные имена MD-файлов

## Контекст

Требование: [docs/requirements/knowledge-base-publishing.md](../requirements/knowledge-base-publishing.md), секция 4.1.

Сейчас pipeline сохраняет `longread.md`, `summary.md`, `story.md` — фиксированные имена. В Obsidian (куда архив подключен по симлинку) все файлы неразличимы. При конвертации в GDoc через md2gdoc документ получает бессмысленное название "longread".

**Цель:** Переименовать MD-файлы в формат `{title} ({speaker}) — {тип}.md`.

## Изменения

### 1. Новый helper в FileSaver

Файл: `backend/app/services/saver.py`

Добавить `_build_md_filename(metadata, suffix) -> str`:
- Формат: `{metadata.title} ({abbreviate_name(metadata.speaker)}) — {suffix}.md`
- Использует существующий `abbreviate_name()` из `speaker_utils.py` (уже импортирован в saver.py)
- Пример: `"Группа поддержки (Дмитрук С.) — лонгрид.md"`
- `@staticmethod` — не зависит от состояния экземпляра

### 2. Обновить 3 приватных метода — добавить параметр `filename`

Файл: `backend/app/services/saver.py`

| Метод | Строка с хардкодом | Было | Станет |
|-------|---------------------|------|--------|
| `_save_longread_md()` | 552 | `"longread.md"` | параметр `filename` |
| `_save_summary_md()` | 580 | `"summary.md"` | параметр `filename` |
| `_save_story_md()` | 608 | `"story.md"` | параметр `filename` |

Каждому добавляется параметр `filename: str`. Внутри: `file_path = archive_path / filename`.

### 3. Обновить 2 публичных метода — генерировать и передавать имя

Файл: `backend/app/services/saver.py`

**`save_educational()`** (строки 146-151):
```python
longread_filename = self._build_md_filename(metadata, "лонгрид")
longread_path = self._save_longread_md(archive_path, longread, longread_filename)

summary_filename = self._build_md_filename(metadata, "саммари")
summary_path = self._save_summary_md(archive_path, summary, summary_filename)
```

**`save_leadership()`** (строка 225):
```python
story_filename = self._build_md_filename(metadata, "история")
story_path = self._save_story_md(archive_path, story, story_filename)
```

### 4. Обновить встроенные тесты

Файл: `backend/app/services/saver.py` (строки ~892-908)

Заменить проверки `"longread.md" in files` на динамические имена. Добавить тест для `_build_md_filename()`.

### 5. Обновить документацию

| Файл | Что обновить |
|------|-------------|
| `docs/pipeline/07-save.md` | Заменить фиксированные имена на паттерн |
| `docs/data-formats.md` | Обновить примеры структуры архива |
| `.claude/rules/content.md` | Обновить описание выходных файлов |

## Не затрагивается

- **Frontend** — отображает `SaveResult.files` как есть, новые имена покажутся автоматически
- **pipeline_results.json** — не содержит ссылок на имена MD-файлов
- **transcript_chunks.json** — фиксированное имя, без изменений
- **Технические файлы** (txt, json, mp3) — фиксированные имена, без изменений

## Чистая архитектура

Никакой поддержки старых имён (`longread.md`, `summary.md`, `story.md`) в коде не остаётся. Хардкоды полностью заменяются на динамическую генерацию. Два существующих архива с материалами переименовываются вручную.

## Верификация

1. `python3 -m py_compile backend/app/services/saver.py` — проверка синтаксиса
2. `cd backend && python3 -m app.services.saver` — встроенные тесты
3. Проверить в Web UI — обработать тестовый файл, убедиться что в "Созданные файлы" показываются новые имена
