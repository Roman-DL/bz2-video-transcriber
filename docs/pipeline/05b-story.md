# 05b. Story (Генерация лидерских историй)

> Альтернатива longread+summarize для content_type=LEADERSHIP

## Обзор

Story Stage генерирует структурированную 8-блочную историю из транскрипта для лидерского контента. Вместо longread.md и summary.md создаётся единый story.md.

## Когда используется

| content_type | Этапы после chunk |
|--------------|-------------------|
| `educational` | longread → summarize → save |
| `leadership` | **story** → save |

## Входные данные

```python
# От clean stage
cleaned_transcript: CleanedTranscript
    text: str           # Очищенный текст
    original_length: int
    cleaned_length: int
    model_name: str

# От parse stage
metadata: VideoMetadata
    content_type: ContentType.LEADERSHIP
    speaker: str        # "Антоновы (Дмитрий и Юлия)"
    event_name: str     # "Форум TABTeam (Москва)"
```

## Выходные данные

```python
class StoryBlock(BaseModel):
    block_number: int   # 1-8
    block_name: str     # "Кто они", "Путь в бизнес", ...
    content: str        # Текст блока

class Story(BaseModel):
    video_id: str
    names: str              # "Дмитрий и Юлия Антоновы"
    current_status: str     # "GET Team"
    event_name: str
    date: str
    main_insight: str       # Главный инсайт

    # 8 блоков
    blocks: list[StoryBlock]

    # Метрики
    time_in_business: str   # "12 лет"
    time_to_status: str     # "8 лет"
    speed: str              # быстро | средне | долго | очень долго
    business_format: str    # клуб | онлайн | гибрид

    # Флаги
    is_family: bool
    had_stagnation: bool
    stagnation_years: int
    had_restart: bool

    # Аналитика
    key_pattern: str        # Ключевой паттерн
    mentor: str
    tags: list[str]
    access_level: str       # consultant | leader | personal
    related: list[str]      # Связанные истории

    # Служебное
    total_blocks: int       # 8
    model_name: str
```

## 8 блоков Story

| № | Название | Содержание |
|---|----------|------------|
| 1 | Кто они | Предыстория: образование, семья, чем занимались до |
| 2 | Путь в бизнес | Как пришли в Herbalife, первый опыт |
| 3 | Рост и вызовы | Этапы развития, трудности, преодоление |
| 4 | Ключ к статусу | Переломный момент, что изменило траекторию |
| 5 | Как устроен бизнес | Формат работы, география, команда |
| 6 | Принципы и советы | Ключевые рекомендации от лидеров |
| 7 | Итоги | Текущие результаты, достижения |
| 8 | Заметки аналитика | Аналитические наблюдения, паттерны |

## Промпт-архитектура

Story использует 3-компонентную архитектуру промптов:

```
config/prompts/
├── story_system.md       # Роль и правила
├── story_instructions.md # Детальные инструкции по блокам
└── story_template.md     # JSON-структура для ответа
```

### Сборка промпта

```python
# В StoryGenerator
system_prompt = load_prompt("story_system")

user_prompt = f"""
{load_prompt("story_instructions")}

## ТРАНСКРИПТ

{cleaned_transcript.text}

## ФОРМАТ ОТВЕТА

{load_prompt("story_template")}
"""
```

## Реализация

### StoryGenerator

```python
# backend/app/services/story_generator.py

class StoryGenerator:
    def __init__(self, ai_client: BaseAIClient, settings: Settings):
        self.ai_client = ai_client
        self.settings = settings

    async def generate(
        self,
        cleaned_transcript: CleanedTranscript,
        metadata: VideoMetadata,
    ) -> Story:
        # Загрузить промпты
        system_prompt = load_prompt("story_system")
        instructions = load_prompt("story_instructions")
        template = load_prompt("story_template")

        # Собрать user prompt
        user_prompt = self._build_prompt(
            instructions, template, cleaned_transcript, metadata
        )

        # Вызвать LLM
        response = await self.ai_client.generate(
            prompt=user_prompt,
            system_prompt=system_prompt,
            temperature=0.7,
        )

        # Парсить JSON ответ
        return self._parse_response(response, metadata)
```

### StoryStage

```python
# backend/app/services/stages/story_stage.py

class StoryStage(BaseStage):
    name = "story"
    depends_on = ["clean", "parse"]

    def should_skip(self, context: StageContext) -> bool:
        """Skip for educational content."""
        metadata = context.get_result("parse")
        return metadata.content_type != ContentType.LEADERSHIP

    async def execute(self, context: StageContext) -> Story:
        cleaned = context.get_result("clean")
        metadata = context.get_result("parse")
        return await self.generator.generate(cleaned, metadata)
```

## Классификация speed

| speed | Критерий |
|-------|----------|
| `быстро` | До статуса < 3 лет |
| `средне` | 3-7 лет |
| `долго` | 7-15 лет |
| `очень долго` | > 15 лет |

## Классификация business_format

| format | Описание |
|--------|----------|
| `клуб` | Физический клуб здорового питания |
| `онлайн` | Только онлайн-консультации |
| `гибрид` | Сочетание офлайн и онлайн |

## Выходной файл

### story.md

```markdown
---
title: "История Антоновых"
names: "Дмитрий и Юлия Антоновы"
current_status: "GET Team"
...
---

# История Антоновых: от консультантов до GET Team

## Главный инсайт
...

## 1. Кто они
...

## 8. Заметки аналитика
...
```

## Отличия от Longread

| Аспект | Longread | Story |
|--------|----------|-------|
| Контент | Обучающие темы | Лидерские истории |
| Структура | Динамическое количество секций | Фиксированно 8 блоков |
| Фокус | Передача знаний | Путь и паттерны лидера |
| Дополнение | + summary.md | Только story.md |
| access_level | int (1-4) | str (consultant/leader/personal) |

## См. также

- [05-longread.md](05-longread.md) — для educational контента
- [06-summarize.md](06-summarize.md) — summary для educational
- [01-parse.md](01-parse.md) — определение content_type
