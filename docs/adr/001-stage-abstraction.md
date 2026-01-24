---
doc_type: adr
status: accepted
created: 2025-01-20
updated: 2026-01-24
audience: [developer]
tags:
  - architecture
  - adr
  - pipeline
  - stages
---

# ADR-001: Stage Abstraction для Pipeline

**Статус:** Принято
**Дата:** 2025-01-20
**Авторы:** Claude Opus 4.5

## Контекст

Система обработки видео состоит из нескольких этапов: парсинг, транскрипция, очистка, чанкирование, генерация лонгрида, саммаризация, сохранение. Текущая реализация в `pipeline.py` (1198 строк) содержит всю логику в одном файле.

**Проблемы:**
1. Добавление нового шага (например, Telegram Summary) требует изменения orchestrator
2. Этапы жёстко связаны — сложно переиспользовать или тестировать изолированно
3. Граф зависимостей implicit — определяется порядком вызовов в коде
4. Нет стандартного способа передачи данных между этапами

## Решение

Ввести абстракцию Stage с тремя основными компонентами:

### 1. BaseStage

Абстрактный базовый класс для этапов обработки:

```python
class BaseStage(ABC):
    name: str                    # Уникальный идентификатор
    depends_on: list[str] = []   # Зависимости
    optional: bool = False       # Можно пропустить?

    @abstractmethod
    async def execute(self, context: StageContext) -> Any:
        pass
```

### 2. StageContext

Immutable контекст для передачи данных между этапами:

```python
@dataclass
class StageContext:
    results: dict[str, Any]      # stage_name -> result
    metadata: dict[str, Any]     # Shared metadata

    def get_result(self, stage_name: str) -> Any
    def with_result(self, stage_name: str, result: Any) -> StageContext
```

### 3. StageRegistry

Реестр для управления этапами и построения pipeline:

```python
class StageRegistry:
    def register(self, stage: BaseStage) -> None
    def build_pipeline(self, stages: list[str]) -> list[BaseStage]
```

## Последствия

### Положительные

1. **Расширяемость**: Новые шаги добавляются без изменения orchestrator
2. **Явные зависимости**: Граф зависимостей декларативный и проверяемый
3. **Изоляция**: Каждый этап можно тестировать независимо
4. **Переиспользование**: Этапы можно комбинировать в разные pipelines
5. **Автоматическая сортировка**: Registry строит правильный порядок выполнения

### Отрицательные

1. **Больше файлов**: 9 файлов вместо 1
2. **Indirection**: Дополнительный уровень абстракции
3. **Кривая обучения**: Нужно понимать паттерн Stage

## Альтернативы

### 1. Оставить monolithic pipeline
- ✗ Не решает проблему расширяемости
- ✓ Проще для понимания

### 2. Использовать существующий workflow engine (Prefect, Dagster)
- ✗ Overhead для простого use case
- ✗ Дополнительная зависимость
- ✓ Больше возможностей (retry, monitoring, etc.)

### 3. Event-driven архитектура
- ✗ Сложнее отлаживать
- ✗ Труднее понять flow
- ✓ Лучшая decoupling

## Примеры использования

### Добавление нового этапа

```python
class TelegramSummaryStage(BaseStage):
    name = "telegram_summary"
    depends_on = ["longread"]
    optional = True

    async def execute(self, context: StageContext) -> TelegramSummary:
        longread = context.get_result("longread")
        # ...
        return TelegramSummary(text=..., hashtags=[...])

# Регистрация
registry.register(TelegramSummaryStage(ai_client, settings))

# Использование
pipeline = registry.build_pipeline([..., "telegram_summary", "save"])
```

### Тестирование изолированного этапа

```python
def test_clean_stage():
    stage = CleanStage(mock_ai_client, settings)
    context = StageContext()
    context = context.with_result("parse", mock_metadata)
    context = context.with_result("transcribe", (mock_transcript, mock_audio))

    result = await stage.execute(context)

    assert isinstance(result, CleanedTranscript)
    assert result.cleaned_length < result.original_length
```

## Структура файлов

```
backend/app/services/stages/
├── __init__.py              # Экспорты и create_default_stages()
├── base.py                  # BaseStage, StageContext, StageRegistry
├── parse_stage.py
├── transcribe_stage.py
├── clean_stage.py
├── chunk_stage.py
├── longread_stage.py
├── summarize_stage.py
└── save_stage.py
```

## Миграция

Фаза 0 создаёт абстракцию параллельно с существующим кодом. Фаза 1 мигрирует orchestrator на использование Stage абстракции.

## Связанные документы

- [docs/pipeline/stages.md](../pipeline/stages.md) — детальная документация
- [docs/architecture.md](../architecture.md) — общая архитектура системы
