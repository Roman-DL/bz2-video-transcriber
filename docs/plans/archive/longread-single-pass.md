# Plan: Единая логика генерации лонгрида (single-pass + map-reduce)

## Контекст

Лонгрид генерируется через map-reduce (TextSplitter → OutlineExtractor → параллельные секции → combine) = 6-12 LLM вызовов. С v0.29 используется только Claude (200K контекст), типичный текст 43K символов (7% контекста).

**Идея:** автоматический выбор пути по размеру контекста модели:
- Текст помещается в контекст → **single-pass** (1 LLM вызов)
- Текст НЕ помещается → **map-reduce** (существующий код)

Это позволяет использовать любые модели (локальные и облачные) без изменения архитектуры.

---

## Решения

| Вопрос | Решение |
|--------|---------|
| Формат вывода | **JSON** — тот же `{introduction, sections[], conclusion, topic_area, tags, access_level}` |
| TextSplitter / OutlineExtractor | **Оставить** — используются в map-reduce пути |
| Промпты | **3 файла для каждого stage** (`system.md` + `instructions.md` + `template.md`). Одинаковая структура для longread и summary |
| Контент промптов | **Обновить** на базе template-prompts. Одни и те же принципы для обоих путей |
| Summary промпты | Обновить в этом же PR |
| Story промпты | Отдельный PR |
| `section.md` / `combine.md` | **Удалить** — мёртвый код, не загружаются через `load_prompt()`. Map-reduce строит секционные/combine промпты inline |

---

## Шаги реализации

### 0. Исправить `get_model_config()` (баг)

**Файл:** `backend/app/config.py` (строки 228, 260)

**Проблема:** `rstrip("0123456789.")` ломает имена Claude моделей:
- `"claude-sonnet-4-6"` → `"claude-sonnet-4-"` → НЕ найдено → defaults (context_tokens не читается)

**Исправление:** в обеих функциях (`load_model_config`, `get_model_config`) — точное совпадение первым:
```python
model_name = model.split(":")[0]
# Exact match (для "claude-sonnet-4-6", "gemma2")
if model_name in config.get("models", {}):
    ...
# Family match fallback (обратная совместимость)
model_family = model_name.rstrip("0123456789.")
if model_family != model_name and model_family in config.get("models", {}):
    ...
# Defaults
```

### 1. Обновить промпты лонгрида (3 файла)

**Директория:** `config/prompts/longread/`

Обновляются на базе `docs/template-prompts/Educational_Longread_Instructions.md`.

| Файл | Назначение | Действие |
|------|-----------|----------|
| `system.md` | Роль и контекст | **Обновить** — обогатить из template-prompts |
| `instructions.md` | Принципы, правила, слайды, RAG | **Обновить** — обогатить из template-prompts |
| `template.md` | JSON шаблон полного вывода | **Обновить** — полный JSON `{introduction, sections[], conclusion, topic_area, tags, access_level}` |

Удалить неиспользуемые файлы: `section.md`, `combine.md` (промпты для map-reduce секций и combine строятся inline в Python-коде, эти файлы никогда не загружаются).

`system.md` + `instructions.md` — общие для обоих путей (single-pass и map-reduce). `template.md` — используется в single-pass; map-reduce строит свои шаблоны inline.

### 2. Обновить промпты конспекта (3 файла)

**Директория:** `config/prompts/summary/`

На базе `docs/template-prompts/Educational_Summary_Instructions.md`:

| Файл | Действие |
|------|----------|
| `system.md` | **Обновить** — обогатить из template-prompts |
| `instructions.md` | **Обновить** — вариативные блоки, правила извлечения |
| `template.md` | **Обновить** — тот же JSON, уточнённые правила заполнения |

JSON формат вывода (`essence`, `key_concepts`, `quotes`, ...) **не меняется**.

### 3. Рефакторинг `longread_generator.py`

**Файл:** `backend/app/services/longread_generator.py`

**Структура:**

```python
class LongreadGenerator:
    def __init__(self, ai_client, settings, prompt_overrides=None):
        # Промпты (3 файла, shared для обоих путей)
        self.system_prompt = load_prompt("longread", "system", settings)
        self.instructions = load_prompt("longread", "instructions", settings)
        self.template = load_prompt("longread", "template", settings)

        # Map-reduce компоненты (используются только если текст не помещается)
        self.text_splitter = TextSplitter()
        self.outline_extractor = OutlineExtractor(ai_client, settings)

        # Определение пути по context_tokens модели
        model_config = get_model_config(settings.longread_model, settings)
        self.context_tokens = model_config.get("context_tokens", 8192)

    async def generate(self, cleaned_transcript, metadata, slides_text=None) -> Longread:
        full_text = self._prepare_text(cleaned_transcript, slides_text)

        if self._fits_in_context(full_text):
            logger.info(f"Single-pass: {len(full_text)} chars fits in {self.context_tokens} context")
            return await self._generate_single_pass(full_text, metadata)
        else:
            logger.info(f"Map-reduce: {len(full_text)} chars exceeds context, splitting")
            return await self._generate_map_reduce(full_text, cleaned_transcript, metadata)

    def _fits_in_context(self, text: str) -> bool:
        """Оценка: Russian ~2.5 tokens/char, overhead ~45K tokens."""
        estimated_tokens = len(text) * 2.5
        available = self.context_tokens * 0.85 - 15_000 - 30_000
        return estimated_tokens < available
```

**Single-pass путь (новый):**
- `_generate_single_pass(text, metadata)` → 1 LLM вызов → JSON → Longread
- `_build_single_pass_prompt(text, metadata)` — system + instructions + задание + транскрипт + template

**Map-reduce путь (существующий, рефакторинг):**
- `_generate_map_reduce(text, cleaned, metadata)` — текущая логика: split → outline → sections → frame
- Все вспомогательные методы сохранены: `_generate_sections()`, `_group_parts()`, `_generate_section()`, `_generate_frame()`
- Секционные и combine промпты строятся inline (как сейчас), используя `self.system_prompt` + `self.instructions`

**Общие методы:**
- `_prepare_text(transcript, slides_text)` — объединение со слайдами
- `_build_longread(data, metadata, tokens, elapsed)` — конструктор Longread из JSON
- `_validate_topic_area()`, `_validate_access_level()` — валидация
- `_parse_json_response()` — парсинг JSON

**Баг-фикс:** `self.settings.summarizer_model` → `self.settings.longread_model`

### 4. Summary — без изменений кода

Промпты обновлены на месте (шаг 2). `SummaryGenerator` загружает те же файлы `system.md`, `instructions.md`, `template.md` — код не меняется.

### 5. Обновить `config/models.yaml`

Добавить `max_input_chars` в `context_profiles.large.longread`:
```yaml
longread:
  max_input_chars: 350000
  chunks_per_section: 10
  max_parallel_sections: 4
```

---

## Логика авто-выбора

| Модель | context_tokens | Доступно (85% - overhead) | Макс символов | Путь для 43K |
|--------|---------------:|------------------------:|-------------:|:--:|
| Claude Sonnet | 200K | ~125K tokens → ~50K chars | ~50K | **single-pass** |
| Claude Haiku | 200K | ~125K tokens → ~50K chars | ~50K | **single-pass** |
| qwen2.5 (32K) | 32K | ~12K tokens → ~5K chars | ~5K | map-reduce |
| gemma2 (8K) | 8K | overhead > context | 0 | map-reduce |

---

## Что НЕ меняется

| Компонент | Почему |
|-----------|--------|
| `backend/app/models/schemas.py` | Longread, Summary модели без изменений |
| `backend/app/api/step_routes.py` | API endpoints без изменений |
| `backend/app/services/pipeline/orchestrator.py` | Вызывает LongreadGenerator тем же способом |
| `backend/app/services/text_splitter.py` | Используется в map-reduce пути |
| `backend/app/services/outline_extractor.py` | Используется в map-reduce пути |
| `backend/app/services/story_generator.py` | Отдельный PR |
| Chunk, Save, Clean, Slides | Не затрагиваются |
| Frontend | API контракт не меняется |

---

## Файлы для создания/изменения

| Действие | Файл |
|----------|------|
| **Исправить** | `backend/app/config.py` (баг get_model_config) |
| **Обновить** | `config/prompts/longread/system.md` |
| **Обновить** | `config/prompts/longread/instructions.md` |
| **Обновить** | `config/prompts/longread/template.md` |
| **Удалить** | `config/prompts/longread/section.md` (мёртвый код) |
| **Удалить** | `config/prompts/longread/combine.md` (мёртвый код) |
| **Обновить** | `config/prompts/summary/system.md` |
| **Обновить** | `config/prompts/summary/instructions.md` |
| **Обновить** | `config/prompts/summary/template.md` |
| **Рефакторинг** | `backend/app/services/longread_generator.py` |
| **Изменить** | `config/models.yaml` (max_input_chars) |

---

## Фазы реализации

### Фаза 1: Код + инфраструктура ✅

- [x] Обновить план с фазами
- [x] Fix `get_model_config()` в `backend/app/config.py`
- [x] Рефакторинг `longread_generator.py` (single-pass + map-reduce + авто-выбор)
- [x] Обновить `config/models.yaml` (max_input_chars)
- [x] Обновить `config/prompts/longread/template.md` (JSON шаблон для single-pass)
- [x] Удалить `config/prompts/longread/section.md`, `combine.md`
- [x] Проверка синтаксиса

### Фаза 2: Промпты + документация ✅

- [x] Обновить `config/prompts/longread/system.md` и `instructions.md`
- [x] Обновить `config/prompts/summary/system.md`, `instructions.md`, `template.md`
- [x] Документация: CLAUDE.md, pipeline.md, ADR-015
- [x] Version bump

---

## Референсный код

- `backend/app/services/story_generator.py` — образец single-pass (паттерн `_build_prompt`)
- `backend/app/services/summary_generator.py` — образец `_truncate_text()`, `_validate_topic_area()`
- `docs/template-prompts/Educational_Longread_Instructions.md` — основа для longread промптов
- `docs/template-prompts/Educational_Summary_Instructions.md` — основа для summary промптов

---

## Верификация

1. `python3 -m py_compile backend/app/services/longread_generator.py && python3 -m py_compile backend/app/config.py`
2. `get_model_config("claude-sonnet-4-6")` возвращает `context_tokens: 200000`
3. Для текста 43K + Claude → single-pass, для малой модели → map-reduce
4. Деплой: `./scripts/deploy.sh`, генерация через UI
5. Регрессия: старый кэш, prompt overrides, map-reduce путь

---

## После реализации

- Обновить `CLAUDE.md`: версия v0.67, архитектура
- Обновить `.claude/rules/pipeline.md`: описание авто-выбора
- Обновить `docs/requirements/longread-single-pass.md`: статус → Implemented
- Предложить ADR и bump version
