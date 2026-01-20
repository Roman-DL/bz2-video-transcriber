# Stage Abstraction

Система абстракций для этапов обработки видео. Позволяет легко добавлять новые шаги в pipeline без изменения оркестратора.

## Обзор

```
backend/app/services/stages/
├── __init__.py              # Экспорты и create_default_stages()
├── base.py                  # BaseStage, StageContext, StageRegistry
├── parse_stage.py           # Парсинг имени файла
├── transcribe_stage.py      # Транскрипция через Whisper
├── clean_stage.py           # Очистка транскрипта
├── chunk_stage.py           # Семантическое чанкирование
├── longread_stage.py        # Генерация лонгрида
├── summarize_stage.py       # Генерация конспекта
└── save_stage.py            # Сохранение результатов
```

## Основные классы

### StageContext

Контекст, передаваемый между стадиями. Хранит результаты предыдущих стадий.

```python
from app.services.stages import StageContext

# Создание контекста
context = StageContext()
context = context.with_metadata("video_path", Path("video.mp4"))

# Добавление результатов
context = context.with_result("parse", metadata)
context = context.with_result("transcribe", (raw_transcript, audio_path))

# Получение результатов
metadata = context.get_result("parse")
raw, audio = context.get_result("transcribe")

# Проверка наличия
if context.has_result("clean"):
    cleaned = context.get_result("clean")
```

### BaseStage

Абстрактный базовый класс для всех стадий.

```python
from app.services.stages import BaseStage, StageContext

class MyStage(BaseStage):
    name = "my_stage"              # Уникальный идентификатор
    depends_on = ["longread"]      # Зависимости
    optional = True                # Опциональная стадия?
    status = ProcessingStatus.SUMMARIZING  # Для прогресса

    async def execute(self, context: StageContext) -> MyResult:
        # Получаем данные из контекста
        longread = context.get_result("longread")

        # Обрабатываем
        result = await self.process(longread)

        return result

    def estimate_time(self, input_size: int) -> float:
        """Оценка времени выполнения в секундах."""
        return 10.0 + input_size / 1000
```

### StageRegistry

Реестр для управления стадиями и построения pipeline.

```python
from app.services.stages import StageRegistry, create_default_stages

# Создание реестра со стандартными стадиями
async with AIClient(settings) as ai_client:
    registry = create_default_stages(ai_client, settings)

# Построение pipeline
stages = registry.build_pipeline(["parse", "transcribe", "clean"])

# Выполнение
context = StageContext().with_metadata("video_path", video_path)
for stage in stages:
    result = await stage.execute(context)
    context = context.with_result(stage.name, result)
```

## Добавление нового шага

### Пример: TelegramSummaryStage

Допустим, нужно генерировать короткое превью для Telegram (~150 символов).

**1. Создать файл `stages/telegram_summary_stage.py`:**

```python
"""Telegram summary stage for generating short previews."""

from app.config import Settings
from app.models.schemas import Longread
from app.services.ai_client import AIClient
from app.services.stages.base import BaseStage, StageContext, StageError
from pydantic import BaseModel


class TelegramSummary(BaseModel):
    """Short summary for Telegram preview."""
    text: str  # ~150 chars
    hashtags: list[str]


class TelegramSummaryStage(BaseStage):
    """Generate short preview for Telegram.

    Input: longread
    Output: TelegramSummary
    """

    name = "telegram_summary"
    depends_on = ["longread"]
    optional = True  # Не обязательный шаг

    def __init__(self, ai_client: AIClient, settings: Settings):
        self.ai_client = ai_client
        self.settings = settings

    async def execute(self, context: StageContext) -> TelegramSummary:
        self.validate_context(context)

        longread: Longread = context.get_result("longread")

        # Генерируем превью
        prompt = f"""
        Создай короткое превью для Telegram (150 символов) на основе лонгрида.

        Заголовок: {longread.title}
        Введение: {longread.introduction}

        Формат ответа:
        - text: краткое описание
        - hashtags: список хэштегов (3-5)
        """

        response = await self.ai_client.generate(
            prompt=prompt,
            model=self.settings.summarizer_model,
        )

        # Парсинг ответа...
        return TelegramSummary(
            text=response[:150],
            hashtags=["#видео", "#обучение"],
        )

    def estimate_time(self, input_size: int) -> float:
        return 5.0
```

**2. Зарегистрировать в `stages/__init__.py`:**

```python
from app.services.stages.telegram_summary_stage import TelegramSummaryStage

__all__ = [
    # ...existing exports...
    "TelegramSummaryStage",
]

def create_default_stages(ai_client, settings, registry=None):
    # ...existing registrations...

    # Добавить новую стадию
    registry.register(TelegramSummaryStage(ai_client, settings))

    return registry
```

**3. Использование:**

```python
# Включить в pipeline
stages = registry.build_pipeline([
    "parse", "transcribe", "clean", "chunk",
    "longread", "telegram_summary", "save"
])

# Результат будет в context.get_result("telegram_summary")
```

## Граф зависимостей

```
parse ─────┬──────────────────────────────────────────────→ save
           │                                                  ↑
           ↓                                                  │
       transcribe                                             │
           │                                                  │
           ↓                                                  │
         clean                                                │
           │                                                  │
           ↓                                                  │
         chunk ───────────────────────────────────────────────┤
           │                                                  │
           ↓                                                  │
       longread ──────────────────────────────────────────────┤
           │                                                  │
           ├──→ summarize ────────────────────────────────────┤
           │                                                  │
           └──→ telegram_summary (optional) ──────────────────┘
```

## API Reference

### StageContext

| Метод | Описание |
|-------|----------|
| `with_result(name, result)` | Добавить результат стадии |
| `get_result(name)` | Получить результат стадии |
| `has_result(name)` | Проверить наличие результата |
| `with_metadata(key, value)` | Добавить метаданные |
| `get_metadata(key, default)` | Получить метаданные |

### BaseStage

| Атрибут | Тип | Описание |
|---------|-----|----------|
| `name` | `str` | Уникальный идентификатор |
| `depends_on` | `list[str]` | Зависимости |
| `optional` | `bool` | Опциональная стадия |
| `status` | `ProcessingStatus` | Статус для прогресса |

| Метод | Описание |
|-------|----------|
| `execute(context)` | Выполнить стадию (async) |
| `estimate_time(input_size)` | Оценить время |
| `validate_context(context)` | Проверить зависимости |

### StageRegistry

| Метод | Описание |
|-------|----------|
| `register(stage)` | Зарегистрировать стадию |
| `get(name)` | Получить стадию по имени |
| `get_all()` | Все стадии в порядке зависимостей |
| `build_pipeline(names)` | Построить pipeline |

## Встроенные тесты

Запуск тестов:

```bash
PYTHONPATH=backend python3 backend/app/services/stages/base.py
```

Вывод:
```
Running Stage abstraction tests...

Test 1: StageContext basic operations... OK
Test 2: StageContext missing result... OK
Test 3: StageRegistry registration... OK
Test 4: Duplicate registration... OK
Test 5: Dependency resolution... OK
Test 6: Circular dependency detection... OK
Test 7: Stage execution... OK
Test 8: validate_context... OK
Test 9: StageError... OK

========================================
All tests passed!
```

## Обработка ошибок

Стадии должны бросать `StageError` при ошибках:

```python
from app.services.stages import StageError

async def execute(self, context: StageContext) -> Result:
    try:
        result = await self.process(data)
        return result
    except ValueError as e:
        raise StageError(self.name, f"Validation failed: {e}", e)
```

Fallback-логика для graceful degradation:

```python
async def execute(self, context: StageContext) -> Result:
    try:
        return await self.process(data)
    except Exception as e:
        logger.warning(f"Stage {self.name} failed: {e}, using fallback")
        return self._create_fallback_result()
```
