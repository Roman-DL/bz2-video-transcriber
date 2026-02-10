# План: Фаза 3 — Генерация лонгрида и истории по content_type

## Цель
Ветвление pipeline по `content_type`:
- **EDUCATIONAL** → LongreadStage → SummarizeStage → `longread.md` + `summary.md`
- **LEADERSHIP** → StoryStage → `story.md` (без summary)

## Принципы реализации

**Чистая архитектура:**
- НЕ реализуем обратную совместимость со старыми методами
- Удаляем устаревший код (старые промпты, старые поля моделей)
- Одна ответственность на компонент (StoryGenerator — только story, LongreadGenerator — только longread)

**Breaking changes:**
- Модель Longread: `section` → `topic_area`, `access_level: int` → `access_level: str`
- Промпты: удаление `longread_section.md` и `longread_combine.md`
- Frontend: новые типы без backwards-compatibility

**Миграция не нужна:**
- Старые обработанные файлы остаются как есть
- Новые файлы создаются в новом формате
- UI показывает то, что есть в данных (graceful degradation уже реализован)

## Архитектура изменений

```
                    ┌─────────────────┐
                    │   ParseStage    │
                    │ (content_type)  │
                    └────────┬────────┘
                             │
              ┌──────────────┴──────────────┐
              ▼                             ▼
    content_type=EDUCATIONAL      content_type=LEADERSHIP
              │                             │
      ┌───────┴───────┐             ┌───────┴───────┐
      ▼               ▼             ▼               │
  LongreadStage  SummarizeStage  StoryStage        │
      │               │             │               │
      ▼               ▼             ▼               │
  longread.md    summary.md     story.md           │
              │               │             │       │
              └───────┬───────┘             │       │
                      └─────────────────────┴───────┘
                                    │
                            ┌───────┴───────┐
                            ▼               ▼
                        SaveStage      SaveStage
                      (educational)   (leadership)
```

## Задачи

### 1. Добавить `should_skip()` в BaseStage
**Файл:** [base.py](backend/app/services/stages/base.py)

```python
class BaseStage(ABC):
    # ... existing ...

    def should_skip(self, context: StageContext) -> bool:
        """Check if stage should be skipped. Override for conditional execution."""
        return False
```

### 2. Добавить модель Story
**Файл:** [schemas.py](backend/app/models/schemas.py)

```python
class StoryBlock(BaseModel):
    block_number: int  # 1-8
    block_name: str    # "Кто они", "Путь в бизнес", etc.
    content: str       # Markdown content

class Story(BaseModel):
    video_id: str
    names: str
    current_status: str
    event_name: str
    date: dt.date
    main_insight: str
    blocks: list[StoryBlock]
    # metadata: speed, business_format, is_family, etc.
    # classification: tags, access_level

    def to_markdown(self) -> str: ...
```

### 3. Создать StoryStage и StoryGenerator
**Файлы:**
- [story_stage.py](backend/app/services/stages/story_stage.py) — новый
- [story_generator.py](backend/app/services/story_generator.py) — новый

```python
class StoryStage(BaseStage):
    name = "story"
    depends_on = ["parse", "chunk"]
    status = ProcessingStatus.LONGREAD  # reuse
    optional = True

    def should_skip(self, context: StageContext) -> bool:
        metadata = context.get_result("parse")
        return metadata.content_type != ContentType.LEADERSHIP
```

**Подход:** Single-shot генерация (не MAP-REDUCE) — история требует полного контекста для хронологии и связей между блоками.

### 4. Модифицировать LongreadStage
**Файл:** [longread_stage.py](backend/app/services/stages/longread_stage.py)

```python
class LongreadStage(BaseStage):
    optional = True  # NEW

    def should_skip(self, context: StageContext) -> bool:
        metadata = context.get_result("parse")
        return metadata.content_type == ContentType.LEADERSHIP
```

### 5. Модифицировать SummarizeStage
**Файл:** [summarize_stage.py](backend/app/services/stages/summarize_stage.py)

```python
class SummarizeStage(BaseStage):
    optional = True  # NEW

    def should_skip(self, context: StageContext) -> bool:
        metadata = context.get_result("parse")
        return metadata.content_type == ContentType.LEADERSHIP
```

### 6. Модифицировать SaveStage
**Файл:** [save_stage.py](backend/app/services/stages/save_stage.py)

- Изменить `depends_on` — сделать longread/summarize/story условными
- Добавить логику выбора по content_type:

```python
async def execute(self, context: StageContext) -> list[str]:
    metadata = context.get_result("parse")

    if metadata.content_type == ContentType.EDUCATIONAL:
        return await self._save_educational(context)
    else:
        return await self._save_leadership(context)
```

### 7. Обновить оркестратор
**Файл:** [orchestrator.py](backend/app/services/pipeline/orchestrator.py)

Добавить проверку `should_skip()` перед выполнением этапа:

```python
for stage in stages:
    if stage.should_skip(context):
        logger.info(f"Skipping {stage.name} (condition not met)")
        continue
    result = await stage.execute(context)
    context = context.with_result(stage.name, result)
```

### 8. Зарегистрировать StoryStage
**Файл:** [stages/__init__.py](backend/app/services/stages/__init__.py)

```python
registry.register(StoryStage(ai_client, settings))

DEFAULT_PIPELINE_STAGES = [
    "parse", "transcribe", "clean", "chunk",
    "longread", "story",  # оба, skip по условию
    "summarize", "save"
]
```

### 9. Создать промпты для story
**Файлы:**
- [story_full.md](config/prompts/story_full.md) — новый

Содержимое: системный промпт + инструкции из `docs/template prompts/Leadership_Story_Instructions.md` + шаблон из `docs/template prompts/Leadership_Story_Template.md`

### 10. Новый подход к промптам: шаблон + инструкции в контексте

**Архитектура промптов:**
```
[Системный промпт] — роль и задача
[Инструкции] — из docs/template prompts/..._Instructions.md
[Шаблон] — из docs/template prompts/..._Template.md
[Данные] — {transcript}, {metadata}, {outline}
```

#### 10.1 Educational Longread

**Новые промпт-файлы:**
- `config/prompts/longread_instructions.md` — копия Educational_Longread_Instructions.md
- `config/prompts/longread_template.md` — копия Educational_Longread_Template.md
- `config/prompts/longread_system.md` — на основе System_Prompts_Examples.md

**Содержимое longread_system.md** (адаптировано для pipeline):
```markdown
Создай лонгрид обучающей темы по шаблону и инструкции.

**Задача:**
1. Прочитай транскрипт полностью
2. Определи структуру темы (разделы по логике автора)
3. Перепиши тему от первого лица, убрав мусор транскрипции
4. Убедись, что каждый раздел самодостаточен для RAG
5. Заполни метаданные

**Важно:**
- Термины уже исправлены — НЕ применяй глоссарий
- Слайды пока не передаются — работай только с транскриптом
```

**Структура вызова LLM:**
```python
system_prompt = load_prompt("longread_system", model, settings)
instructions = load_prompt("longread_instructions", model, settings)
template = load_prompt("longread_template", model, settings)

full_prompt = f"""
{system_prompt}

## ИНСТРУКЦИИ
{instructions}

## ШАБЛОН ВЫХОДНОГО ДОКУМЕНТА
{template}

## КОНТЕКСТ
- Событие: {metadata.event_type}
- Дата: {metadata.date}
- Спикер: {metadata.speaker}

## КОНТЕКСТ (OUTLINE)
{outline}

## ОЧИЩЕННЫЙ ТРАНСКРИПТ
{transcript}
"""
```

**Новая классификация (topic_area):**
- продажи, спонсорство, лидерство
- мотивация, инструменты, маркетинг-план

**Новые access_level:**
- consultant | leader | personal (вместо 1-4)

#### 10.2 Leadership Story

**Новые промпт-файлы:**
- `config/prompts/story_instructions.md` — копия Leadership_Story_Instructions.md
- `config/prompts/story_template.md` — копия Leadership_Story_Template.md
- `config/prompts/story_system.md` — на основе System_Prompts_Examples.md

**Содержимое story_system.md** (адаптировано для pipeline):
```markdown
Создай конспект лидерской истории по шаблону и инструкции.

**Задача:**
1. Прочитай транскрипт полностью
2. Заполни релевантные блоки шаблона (пустые блоки удалить)
3. Выдели 2-3 ключевые цитаты
4. Заполни метаданные (особенно speed, format, keywords)
5. Определи «Для кого эта история»
6. Сформулируй главный инсайт

**Важно:**
- Термины уже исправлены — НЕ применяй глоссарий
- Слайды пока не передаются — работай только с транскриптом
```

**Структура вызова LLM:**
```python
full_prompt = f"""
{system_prompt}

## ИНСТРУКЦИИ
{instructions}

## ШАБЛОН ВЫХОДНОГО ДОКУМЕНТА
{template}

## КОНТЕКСТ
- Событие: {metadata.event_name}
- Дата: {metadata.date}
- Спикер: {metadata.speaker}

## КОНТЕКСТ (OUTLINE)
{outline}

## ОЧИЩЕННЫЙ ТРАНСКРИПТ
{transcript}
"""
```

#### 10.3 Изменения в моделях

**Longread (schemas.py):**
```python
# Было
section: str = "Обучение"  # Обучение|Продукты|Бизнес|Мотивация
access_level: int = 1  # 1-4

# Стало
topic_area: list[str] = []  # продажи, спонсорство, лидерство, ...
access_level: str = "consultant"  # consultant|leader|personal
speaker_status: str = ""
publish_gdocs: bool = False
gdocs_url: str = ""
related: list[str] = []
```

**Убрать:** глоссарий из промптов (термины исправлены на clean).

## Файлы для изменения

### Модели и логика
| Файл | Изменение |
|------|-----------|
| `backend/app/services/stages/base.py` | Добавить `should_skip()` |
| `backend/app/models/schemas.py` | Story, StoryBlock, обновить Longread (topic_area, access_level) |
| `backend/app/services/stages/story_stage.py` | НОВЫЙ |
| `backend/app/services/story_generator.py` | НОВЫЙ |
| `backend/app/services/longread_generator.py` | Новая архитектура промптов |
| `backend/app/services/stages/longread_stage.py` | Добавить `should_skip()` |
| `backend/app/services/stages/summarize_stage.py` | Добавить `should_skip()` |
| `backend/app/services/stages/save_stage.py` | Условное сохранение |
| `backend/app/services/pipeline/orchestrator.py` | Проверка `should_skip()` |
| `backend/app/services/stages/__init__.py` | Регистрация StoryStage |
| `backend/app/services/saver.py` | Метод `save_leadership()` |

### Промпты Educational Longread
| Файл | Источник |
|------|----------|
| `config/prompts/longread_system.md` | НОВЫЙ: системный промпт |
| `config/prompts/longread_instructions.md` | Копия Educational_Longread_Instructions.md |
| `config/prompts/longread_template.md` | Копия Educational_Longread_Template.md |

### Промпты Leadership Story
| Файл | Источник |
|------|----------|
| `config/prompts/story_system.md` | НОВЫЙ: системный промпт |
| `config/prompts/story_instructions.md` | Копия Leadership_Story_Instructions.md |
| `config/prompts/story_template.md` | Копия Leadership_Story_Template.md |

### Удалить старые промпты
- `config/prompts/longread_section.md` — заменён на system + instructions + template
- `config/prompts/longread_combine.md` — заменён на system + instructions + template

### Фронтенд

| Файл | Изменение |
|------|-----------|
| `frontend/src/api/types.ts` | Добавить Story, StoryBlock интерфейсы; обновить VideoMetadata (content_type, event_category) |
| `frontend/src/components/results/StoryView.tsx` | НОВЫЙ: компонент для отображения 8 блоков истории |
| `frontend/src/components/processing/StepByStep.tsx` | Условное отображение: Story для leadership, Longread+Summary для educational |
| `frontend/src/components/archive/ArchiveResultsModal.tsx` | Добавить блок Story, условная логика по content_type |
| `frontend/src/components/results/LongreadView.tsx` | Обновить метаданные: topic_area вместо section |
| `frontend/src/components/results/SummaryView.tsx` | Обновить метаданные |

**Ключевые изменения в types.ts:**
```typescript
// Добавить в VideoMetadata
export interface VideoMetadata {
  // ... existing ...
  content_type: 'educational' | 'leadership';
  event_category: 'regular' | 'offsite';
  event_name?: string;
}

// Новый интерфейс
export interface Story {
  video_id: string;
  names: string;
  current_status: string;
  main_insight: string;
  blocks: StoryBlock[];
  tags: string[];
  access_level: string;
  model_name: string;
}

// Обновить PipelineResults
export interface PipelineResults {
  // ... existing ...
  story?: Record<string, unknown>;
}
```

**Условная логика в компонентах:**
```typescript
// В StepByStep/ArchiveResultsModal
if (metadata.content_type === 'leadership') {
  // Показать StoryView
} else {
  // Показать LongreadView + SummaryView
}
```

## Порядок реализации

### Backend (этапы 1-10)
1. **Модели** — Story, StoryBlock, обновить Longread (topic_area, access_level)
2. **Base** — should_skip() в BaseStage
3. **Промпты educational** — создать longread_system/instructions/template.md
4. **LongreadGenerator** — новая архитектура (system + instructions + template)
5. **Промпты leadership** — создать story_system/instructions/template.md
6. **StoryGenerator** — story_generator.py
7. **StoryStage** — story_stage.py, регистрация
8. **Условные skip** — LongreadStage, SummarizeStage
9. **SaveStage** — условное сохранение
10. **Orchestrator** — проверка should_skip()

### Frontend (этапы 11-14)
11. **Types** — обновить types.ts (VideoMetadata, Story, PipelineResults)
12. **StoryView** — создать компонент для 8 блоков
13. **StepByStep** — условное отображение по content_type
14. **ArchiveResultsModal** — поддержка Story блока

### Документация (этап 15)
15. **Docs** — обновить CLAUDE.md, pipeline docs, data-formats.md

## Обновление документации

### Критические документы

| Документ | Изменения |
|----------|-----------|
| [CLAUDE.md](CLAUDE.md) | Обновить Longread модель: `section → topic_area`, `access_level 1-4 → consultant/leader/personal`. Добавить Story |
| [docs/pipeline/05-longread.md](docs/pipeline/05-longread.md) | Полная переработка: новая архитектура промптов, модель, should_skip() |
| [docs/pipeline/stages.md](docs/pipeline/stages.md) | Добавить should_skip() в BaseStage, обновить граф зависимостей |
| [docs/data-formats.md](docs/data-formats.md) | Обновить longread.md frontmatter, добавить story.md формат |
| [docs/pipeline/07-save.md](docs/pipeline/07-save.md) | Условное сохранение по content_type |

### Новые документы

| Документ | Описание |
|----------|----------|
| [docs/pipeline/05a-story.md](docs/pipeline/05a-story.md) | НОВЫЙ: документация по StoryStage (8 блоков, single-shot) |

### Обновить план оптимизации

**Файл:** [docs/research/pipeline-optimization-for-rag.md](docs/research/pipeline-optimization-for-rag.md)

Отметить Фазу 3 как завершённую.

### Ключевые изменения в data-formats.md

**longread.md frontmatter (было → стало):**
```yaml
# Было
section: "Обучение"
access_level: 1

# Стало
topic_area:
  - продажи
  - инструменты
access_level: consultant
speaker_status: "GET"
```

**Добавить story.md формат:**
```yaml
---
type: leadership-story
names: "Дмитрий и Юлия Антоновы"
current_status: "President's Team"
event: "Форум TABTeam (Москва)"
date: 2025-01-15
time_in_business: "12 лет"
speed: "средне"
business_format: "гибрид"
is_family: true
had_stagnation: true
---
```

## Верификация

### Тест 1: Educational pipeline
```bash
# Файл: 2025.01.13 ПШ.SV Тема (Спикер).mp4
# Ожидание: content_type=EDUCATIONAL
# Выходные файлы: longread.md, summary.md
# Пропущен: StoryStage
```

### Тест 2: Leadership pipeline
```bash
# Файл: Антоновы (Дмитрий и Юлия).mp4 (из папки выездного)
# Ожидание: content_type=LEADERSHIP
# Выходные файлы: story.md
# Пропущены: LongreadStage, SummarizeStage
```

### Проверки
- [ ] Story.to_markdown() генерирует корректный YAML frontmatter
- [ ] 8 блоков заполняются согласно шаблону
- [ ] Пустые блоки не включаются в вывод
- [ ] Логи показывают "Skipping longread" для leadership
- [ ] Логи показывают "Skipping story" для educational
