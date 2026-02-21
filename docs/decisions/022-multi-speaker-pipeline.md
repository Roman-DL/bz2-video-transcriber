# ADR-022: Мультиспикерный контент в pipeline

**Статус:** Принято
**Дата:** 2026-02-22
**Requirement:** [docs/requirements/multi-speaker-support.md](../requirements/multi-speaker-support.md)

## Контекст

MD-транскрипты из MacWhisper содержат метки спикеров (`Фамилия Имя`, `SpeakerN`). В v0.64 реализована инфраструктура: `SpeakerInfo`, `parse_speakers()`, `VideoMetadata.speaker_info`. Но stages и saver не использовали `speaker_info` — Claude не получал инструкций по работе с мультиспикерным контентом.

Сценарии: со-спикеры (2 именованных), линейка (3+), Q&A (SpeakerN), комбинации.

## Решения

### 1. Условные секции в существующих промптах (не отдельные файлы)

**Выбор:** Добавить секцию «Мультиспикерный контент» в конец каждого `instructions.md`.

**Альтернатива:** Отдельные файлы `instructions_multi.md` + prompt_overrides.

**Почему так:** 80% инструкций общие (структура, стиль, RAG-ready). Отдельные файлы → дублирование и рассинхрон. Секция ~200 слов, Claude легко обрабатывает. Условие «Применяй ТОЛЬКО если в задании есть блок» + `build_speaker_context() → []` для single → промпт не меняется для односпикерных тем.

### 2. Speaker context как `*list` unpacking в prompt_parts

**Выбор:** `build_speaker_context()` возвращает `list[str]`, вставляется через `*build_speaker_context(...)`.

**Почему так:** Пустой список `[]` при `single/None` → промпт идентичен текущему (zero-impact). Нет условных `if` в каждом генераторе — одна строка вставки. Покрывает все сценарии единообразно.

### 3. Lineup — educational, не leadership

**Выбор:** Линейка (3+ спикеров) → educational pipeline (longread + summary), не story.

**Почему так:** Линейка — это набор мини-выступлений с модератором. Story предполагает 8-блочный анализ одной лидерской истории. Story-промпт получил минимальные изменения (только со-спикеры), линейка обрабатывается через longread.

**Важно для будущих доработок story:** при рефакторинге story-инструкций учитывать, что story видит только `co_speakers` / `co_speakers_qa`, НЕ `lineup`.

### 4. Saver: regex только при `is_lineup`

**Выбор:** `LINEUP_NAME_RE = re.compile(r"\(([^)]+)\)$")` применяется **ТОЛЬКО** при `scenario in ("lineup", "lineup_qa")`.

**Альтернатива:** Универсальный парсинг скобок из H2 для всех сценариев.

**Почему так:** Обычные H2 могут содержать скобки (`## Инструмент (практика)`). Regex для извлечения имени участника из `## Тема (Фамилия Имя)` сработает на false positive без guard clause. При `is_lineup=False` regex не вызывается → нулевой риск для существующих тем.

### 5. Speaker context во всех 3 методах longread

**Выбор:** Вставка в `_build_single_pass_prompt()`, `_build_section_prompt()`, `_build_frame_prompt()`.

**Почему так:** Longread имеет два пути (single-pass и map-reduce). Map-reduce вызывает section и frame промпты отдельно. Без вставки в оба пути — мультиспикерный контекст терялся бы при использовании Ollama/малоконтекстных моделей.

## Последствия

- При `speaker_info=None` (Whisper, legacy) — поведение идентично до v0.79
- Промпты длиннее на ~200 слов — незначительно для Claude
- Saver формирует адаптивные шапки: `Спикеры:` для co_speakers, `Участник:` per-chunk для lineup
- `metadata.speaker` в JSON: со-спикеры → abbreviated через запятую, lineup → ведущий (из имени файла)
