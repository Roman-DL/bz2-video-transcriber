# План: Поддержка мультиспикерного контента в pipeline

## Контекст

MD-транскрипты из MacWhisper содержат метки спикеров. В v0.64 реализована инфраструктура: `SpeakerInfo`, `parse_speakers()`, `VideoMetadata.speaker_info`. Но stages и saver не используют `speaker_info` — Claude не получает инструкций по работе с мультиспикерным контентом, шапки чанков не адаптируются. Требование: [docs/requirements/multi-speaker-support.md](../requirements/multi-speaker-support.md).

## Файлы для изменения

| # | Файл | Что меняется |
|---|------|-------------|
| 1 | `backend/app/utils/speaker_utils.py` | +`build_speaker_context()`, +`abbreviate_name()`, +self-tests |
| 2 | `backend/app/services/longread_generator.py` | +import, speaker context в 3 метода prompt builder |
| 3 | `backend/app/services/summary_generator.py` | +import, speaker context в `_build_prompt()` |
| 4 | `backend/app/services/story_generator.py` | +import, speaker context в `_build_prompt()` |
| 5 | `config/prompts/longread/instructions.md` | +секция "Мультиспикерный контент" в конце |
| 6 | `config/prompts/summary/instructions.md` | +секция "Мультиспикерный контент" в конце |
| 7 | `config/prompts/story/instructions.md` | +секция "Мультиспикерный контент" в конце |
| 8 | `backend/app/services/saver.py` | Адаптация шапки чанка по сценарию |

---

## Шаг 1. Утилиты в `speaker_utils.py`

### `abbreviate_name(full_name: str) -> str`

`"Беркин Андрей"` → `"Беркин А."`. Используется в saver для шапок чанков.

### `build_speaker_context(speaker_info, host_name=None) -> list[str]`

Формирует блок контекста для user prompt. Возвращает `list[str]` для вставки в `prompt_parts`.

- `speaker_info is None` или `scenario == "single"` → `[]` (пустой список, промпт не меняется)
- Остальные сценарии → строки вида:
  ```

  ## Мультиспикерный контент
  Тип: со-спикеры
  Спикеры: Беркин Андрей, Дмитрук Светлана
  ```
- Для lineup: `host_name` (из `metadata.speaker`) определяет ведущего. `named_speakers` сортированы по алфавиту в `parse_speakers()`, поэтому порядок появления не сохраняется → нужен явный host.
- Q&A: `Есть Q&A: да (Speaker3, Speaker5)`

Self-tests: `abbreviate_name` + `build_speaker_context` для всех сценариев (single, co_speakers, lineup, qa, co_speakers_qa, lineup_qa, None).

---

## Шаг 2. Интеграция в генераторы (3 файла, однотипно)

Паттерн одинаковый — unpacking `*build_speaker_context(...)` в list literal `prompt_parts = [...]`:

### longread_generator.py — 3 точки вставки

Импорт: `from app.utils.speaker_utils import build_speaker_context`

**a) `_build_single_pass_prompt()`** (строка 310-313) — после `**Событие:**`:
```python
f"**Событие:** {metadata.event_type}",
*build_speaker_context(metadata.speaker_info, metadata.speaker),
```

**b) `_build_section_prompt()`** (строка 532-533) — после `**Тема:**`:
```python
f"**Тема:** {metadata.title}",
*build_speaker_context(metadata.speaker_info, metadata.speaker),
```

**c) `_build_frame_prompt()`** (строка 620-623) — после `**Событие:**`:
```python
f"**Событие:** {metadata.event_type}",
*build_speaker_context(metadata.speaker_info, metadata.speaker),
```

Покрывает **оба** пути (single-pass И map-reduce) → митигация риска #2.

### summary_generator.py — 1 точка

Импорт: `from app.utils.speaker_utils import build_speaker_context`

**`_build_prompt()`** (строка 310-313) — после `**Событие:**`:
```python
f"**Событие:** {metadata.event_type}",
*build_speaker_context(metadata.speaker_info, metadata.speaker),
```

### story_generator.py — 1 точка

Импорт: `from app.utils.speaker_utils import build_speaker_context`

**`_build_prompt()`** (строка 207-209) — после `**Дата:**`:
```python
f"**Дата:** {metadata.date.isoformat()}",
*build_speaker_context(metadata.speaker_info, metadata.speaker),
```

---

## Шаг 3. Промпты — условные секции

Во все 3 файла добавляется секция в конец с обязательным условием:

> **Применяй ТОЛЬКО если в задании есть блок «Мультиспикерный контент».** Без него — игнорируй эту секцию полностью.

### longread/instructions.md (после строки 174)

- **Со-спикеры:** от третьего лица, атрибуция через "по словам {Имя}". Правило "Реплики ведущих → убрать" НЕ применяется к со-спикерам
- **Линейка:** H2 формат `## Тема (Фамилия Имя)` per participant. Уточняющие вопросы ведущего — часть контента
- **Q&A:** раздел `## Вопросы и ответы`, формат **Вопрос:**/**Ответ:**, убрать SpeakerN

### summary/instructions.md (после строки 98)

- Цитаты с атрибуцией: `> «Цитата» — Беркин А.`
- Линейка: подразделы `### Фамилия Имя`
- Q&A: блок "Вопросы и ответы"

### story/instructions.md (после строки 145)

- Минимально: со-спикеры — атрибуция идей каждому, `names` через " и "

---

## Шаг 4. Saver — адаптация шапки чанка

Файл: `saver.py`, метод `_save_chunks_json()` (строки 402-414).

Импорт: `import re` + `from app.utils.speaker_utils import abbreviate_name`

### Логика формирования шапки по сценарию

| Сценарий | Строка шапки | Пример |
|----------|-------------|--------|
| `None` / `single` / `qa` | `Спикер: {speaker} \| событие \| дата` | Текущая логика без изменений |
| `co_speakers` / `co_speakers_qa` | `Спикеры: Имя1, Имя2 \| событие \| дата` | `Спикеры: Беркин А., Дмитрук С. \| ФСТ \| 22.02.2026` |
| `lineup` / `lineup_qa` | Per-chunk: `Участник: {имя} \| Линейка, ведущий: {вед.} \| событие \| дата` | `Участник: Беркин Андрей \| Линейка, ведущий: Дмитрук С. \| ФСТ \| 22.02.2026` |

### Lineup: regex извлечение участника

```python
LINEUP_NAME_RE = re.compile(r"\(([^)]+)\)$")
```

Применяется **ТОЛЬКО** при `scenario in ("lineup", "lineup_qa")` → митигация риска #3. Если regex не матчит (intro/Q&A раздел) → стандартная шапка с `metadata.speaker`.

### `metadata.speaker` в JSON materials

- `co_speakers` → `"Беркин А., Дмитрук С."` (abbreviated, через запятую)
- `lineup` → `metadata.speaker` (ведущий из имени файла)
- Остальное → без изменений

---

## Митигация рисков (из требования §7)

| Риск | Митигация | Проверка |
|------|-----------|----------|
| #1 Промпт-блоат | Явное условие "ТОЛЬКО если в задании есть блок" | `build_speaker_context()` → `[]` для single → блок не появляется |
| #2 Map-reduce путь | Speaker context в **3** метода longread (single-pass, section, frame) | Code review: все `_build_*_prompt()` содержат вставку |
| #3 Saver regex false positive | Regex `\(([^)]+)\)$` **ТОЛЬКО** при `is_lineup == True` | Для single/co_speakers regex не вызывается |
| #4 "Реплики ведущих" ослабление | Уточнение привязано к блоку контекста, не к базовой инструкции | Без блока "Мультиспикерный контент" уточнение не видно Claude |

---

## Верификация

1. **Синтаксис:** `python3 -m py_compile` для всех 4 Python-файлов
2. **Self-tests:** `python3 backend/app/utils/speaker_utils.py` — проверка новых функций
3. **Self-tests saver:** `python3 backend/app/services/saver.py` — существующие тесты (односпикерный) должны пройти без изменений
4. **Обратная совместимость:** при `speaker_info=None` генераторы и saver работают идентично текущему поведению
