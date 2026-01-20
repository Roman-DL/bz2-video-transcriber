# ADR-002: Декомпозиция pipeline.py

## Статус

Принято (2025-01-20)

## Контекст

Файл `pipeline.py` вырос до ~1200 строк и смешивает четыре ответственности:

1. **Orchestration** — координация этапов обработки
2. **Progress tracking** — STAGE_WEIGHTS, расчёт прогресса
3. **Fallback logic** — 4 метода _create_fallback_*
4. **Configuration** — _get_settings_with_model для override моделей

Это нарушает Single Responsibility Principle и усложняет:
- Тестирование отдельных компонентов
- Добавление новых fallback стратегий
- Изменение логики прогресса без риска сломать оркестрацию

## Решение

Декомпозировать `pipeline.py` на пакет `pipeline/` с независимыми модулями:

```
backend/app/services/pipeline/
├── __init__.py                  # Экспорт PipelineOrchestrator
├── orchestrator.py              # Lean orchestrator
├── progress_manager.py          # STAGE_WEIGHTS, progress calculation
├── fallback_factory.py          # Все _create_fallback_* методы
└── config_resolver.py           # _get_settings_with_model
```

### Компоненты

#### ProgressManager

```python
class ProgressManager:
    STAGE_WEIGHTS = {...}  # Веса этапов

    def calculate_overall_progress(stage, stage_progress) -> float
    async def update_progress(callback, status, stage_progress, message)
```

Централизует логику расчёта прогресса. Можно легко изменить веса или алгоритм без затрагивания orchestrator.

#### FallbackFactory

```python
class FallbackFactory:
    def create_chunks(cleaned_transcript, metadata) -> TranscriptChunks
    def create_summary(metadata) -> VideoSummary
    def create_longread(metadata, chunks) -> Longread
    def create_summary_from_longread(longread, metadata) -> Summary
```

Инкапсулирует создание fallback объектов. Можно добавить новые fallback стратегии (например, разные уровни degradation) без изменения orchestrator.

#### ConfigResolver

```python
class ConfigResolver:
    def with_model(model, stage) -> Settings
    def get_model_for_stage(stage) -> str
```

Управляет override моделей для step-by-step режима. Изолирует логику создания Settings копий.

#### PipelineOrchestrator

Остаётся lean координатором:
- Использует `ProgressManager` через композицию
- Использует `FallbackFactory` через композицию
- Использует `ConfigResolver` через композицию
- Сохраняет backward-compatible методы как deprecated wrappers

### Использование

```python
# Внешний API не меняется
from app.services.pipeline import PipelineOrchestrator, PipelineError

orchestrator = PipelineOrchestrator()
result = await orchestrator.process(video_path)

# Новые компоненты доступны при необходимости
from app.services.pipeline import ProgressManager, FallbackFactory, ConfigResolver

# Использование компонентов напрямую
manager = ProgressManager()
progress = manager.calculate_overall_progress(ProcessingStatus.TRANSCRIBING, 50)

factory = FallbackFactory(settings)
chunks = factory.create_chunks(cleaned_transcript, metadata)
```

## Последствия

### Положительные

- **Single Responsibility**: каждый модуль — одна обязанность
- **Тестируемость**: можно тестировать ProgressManager отдельно от orchestrator
- **Расширяемость**: новые fallback стратегии добавляются в FallbackFactory
- **Читаемость**: orchestrator.py теперь ~500 строк вместо 1200
- **Backward compatibility**: существующие импорты продолжают работать

### Отрицательные

- **Больше файлов**: 4 файла вместо 1
- **Косвенность**: нужно смотреть в несколько файлов для полной картины
- **Deprecated wrappers**: временно остаются для совместимости

## Альтернативы

### 1. Оставить как есть

Отклонено — файл слишком большой, нарушает SRP.

### 2. Вынести только fallback

Частичное решение. Прогресс и конфигурация всё ещё смешаны с оркестрацией.

### 3. Использовать mixins

Отклонено — mixins скрывают зависимости и усложняют понимание кода.

## Связанные документы

- [architecture.md](../architecture.md) — обновлённая архитектура
- [001-stage-abstraction.md](001-stage-abstraction.md) — Stage абстракция
- [CLAUDE.md](../../CLAUDE.md) — структура проекта

## Примечания

После удаления deprecated wrappers в следующих версиях, `orchestrator.py` станет ещё компактнее (~400 строк).
