# Рефакторинг архитектуры bz2-video-transcriber

## Цель

Оптимизация текущей архитектуры с подготовкой к поддержке облачных моделей (Claude API) и кэширования промежуточных результатов.

## Ключевые решения

- **Приоритет**: Сначала декомпозиция, потом функциональность
- **Провайдер**: Claude API (Anthropic) — единственный облачный провайдер
- **API**: Чистое решение без версионирования, фронтенд обновляем вместе

---

## Текущие проблемы

### pipeline.py (1198 строк)
Смешаны 4 ответственности:
- Orchestration (координация этапов)
- Progress tracking (STAGE_WEIGHTS, расчёт прогресса)
- Fallback logic (4 метода _create_fallback_*)
- Configuration (_get_settings_with_model)

### chunker.py (799 строк)
- `chunk()` и `chunk_with_outline()` дублируют ~95% кода
- MapReduce логика встроена без абстракции
- JSON extraction, chunk merging можно переиспользовать

---

## План рефакторинга

### Фаза 0: Абстракция Stage (расширяемость)

**Цель**: Упростить добавление новых шагов обработки (например, Telegram Summary).

**Файлы для создания:**

```
backend/app/services/stages/
├── __init__.py
├── base.py                      # BaseStage, StageContext, StageRegistry
├── parse_stage.py               # ParseStage
├── transcribe_stage.py          # TranscribeStage
├── clean_stage.py               # CleanStage
├── chunk_stage.py               # ChunkStage
├── longread_stage.py            # LongreadStage
├── summarize_stage.py           # SummarizeStage
├── save_stage.py                # SaveStage
└── telegram_summary_stage.py    # TelegramSummaryStage (пример нового шага)
```

**Базовый класс:**

```python
class BaseStage(ABC):
    name: str                           # "telegram_summary"
    depends_on: list[str] = []          # ["longread"]
    optional: bool = False              # Можно пропустить?

    @abstractmethod
    async def execute(self, context: StageContext) -> BaseModel:
        """Выполнить шаг, вернуть результат."""
        pass

    def estimate_time(self, input_size: int) -> float:
        """Оценить время выполнения."""
        pass

class StageRegistry:
    """Централизованный реестр шагов."""

    def register(self, stage: BaseStage) -> None: ...
    def get(self, name: str) -> BaseStage: ...
    def build_pipeline(self, stages: list[str]) -> list[BaseStage]: ...
```

**Пример добавления нового шага:**

```python
# stages/telegram_summary_stage.py
class TelegramSummaryStage(BaseStage):
    name = "telegram_summary"
    depends_on = ["longread"]
    optional = True  # Не обязательный шаг

    async def execute(self, context: StageContext) -> TelegramSummary:
        longread = context.get("longread")
        # Генерация ~150 символов для превью в Telegram
        return TelegramSummary(text=..., hashtags=[...])

# Регистрация
registry.register(TelegramSummaryStage())
```

**Критические файлы:**
- [pipeline.py](backend/app/services/pipeline.py) — рефакторинг под Stage абстракцию

**Документация после Фазы 0:**
- [ ] Docstrings для `BaseStage`, `StageContext`, `StageRegistry`
- [ ] Встроенные тесты в base.py
- [ ] Обновить [architecture.md](docs/architecture.md) — диаграмма Stage абстракции
- [ ] Создать [docs/pipeline/stages.md](docs/pipeline/stages.md) — как добавлять новые шаги
- [ ] Обновить [CLAUDE.md](CLAUDE.md) — информация о Stage Registry

---

### Фаза 1: Декомпозиция pipeline.py

**Файлы для создания:**

```
backend/app/services/pipeline/
├── __init__.py                  # Экспорт PipelineOrchestrator
├── orchestrator.py              # Lean orchestrator (~400 строк)
├── progress_manager.py          # STAGE_WEIGHTS, progress calculation
├── fallback_factory.py          # Все _create_fallback_* методы
└── config_resolver.py           # _get_settings_with_model
```

**Изменения:**
1. Вынести `ProgressManager` класс с методами `_update_progress`, `_calculate_overall_progress`
2. Вынести `FallbackFactory` класс с методами создания fallback объектов
3. Вынести `ConfigResolver` для управления Settings overrides
4. Оставить в `PipelineOrchestrator` только координацию этапов

**Критические файлы:**
- [pipeline.py](backend/app/services/pipeline.py) — основной файл для декомпозиции

**Документация после Фазы 1:**
- [ ] Docstrings для `ProgressManager`, `FallbackFactory`, `ConfigResolver`
- [ ] Встроенные тесты в каждом модуле
- [ ] Обновить [architecture.md](docs/architecture.md) — диаграмма pipeline/ модулей
- [ ] Создать ADR: "Декомпозиция pipeline.py" (почему так разделили)

---

### Фаза 2: Декомпозиция chunker.py

**Файлы для создания:**

```
backend/app/utils/
├── json_utils.py                # extract_json(), parse_json_safe()
├── chunk_utils.py               # merge_small_chunks(), validate_chunks()
└── token_utils.py               # estimate_tokens(), calculate_num_predict()
```

**Изменения:**
1. Объединить `chunk()` и `chunk_with_outline()` в один метод с опциональными параметрами
2. Вынести JSON extraction в shared utils
3. Вынести chunk merging/validation в shared utils
4. Удалить дублирование кода (~250 строк экономии)

**Критические файлы:**
- [chunker.py](backend/app/services/chunker.py) — дедупликация и выделение utils

**Документация после Фазы 2:**
- [ ] Docstrings для `json_utils`, `chunk_utils`, `token_utils`
- [ ] Встроенные тесты для utils
- [ ] Обновить [data-formats.md](docs/data-formats.md) — формат chunk JSON
- [ ] Создать ADR: "Shared utils для LLM сервисов"

---

### Фаза 3: Абстракция AI клиентов (заглушка для облака)

**Файлы для создания:**

```
backend/app/services/ai_clients/
├── __init__.py
├── base.py                      # BaseAIClient (Protocol/ABC)
├── ollama_client.py             # Текущий AIClient → OllamaClient
└── claude_client.py             # Заглушка CloudClient (NotImplemented)
```

**Расширение config/models.yaml — Context Profiles:**

```yaml
# Параметры разбиения привязаны к размеру контекста, не к модели
context_profiles:
  small:    # < 16K tokens
    chunk_size: 6000
    overlap: 1500
    large_text_threshold: 10000
    target_chunk_words: 300
    min_chunk_words: 100

  medium:   # 16K - 64K tokens
    chunk_size: 20000
    overlap: 3000
    large_text_threshold: 40000
    target_chunk_words: 500
    min_chunk_words: 200

  large:    # > 100K tokens (облачные модели)
    chunk_size: 100000
    overlap: 10000
    large_text_threshold: 200000
    target_chunk_words: 1000
    min_chunk_words: 400

providers:
  ollama:
    type: "local"
    default_profile: small      # Профиль по умолчанию

  claude:
    type: "cloud"
    default_profile: large
    api_key_env: "ANTHROPIC_API_KEY"

models:
  gemma2:9b:
    provider: ollama
    context_tokens: 8192
    context_profile: small      # Ссылка на профиль

  qwen2.5:14b:
    provider: ollama
    context_tokens: 32768
    context_profile: medium

  claude-sonnet:
    provider: claude
    context_tokens: 200000
    context_profile: large
    # Заглушка — реализация в Фазе 5
```

**Преимущества Context Profiles:**
- DRY — параметры определяются один раз для профиля
- Можно override для конкретной модели если нужно
- Логика выбора параметров понятна
- Легко добавить новую модель — только указать профиль

**Критические файлы:**
- [ai_client.py](backend/app/services/ai_client.py) — рефакторинг в OllamaClient
- [models.yaml](config/models.yaml) — расширение конфигурации

**Документация после Фазы 3:**
- [ ] Docstrings для `BaseAIClient`, `OllamaClient`
- [ ] Обновить [configuration.md](docs/configuration.md) — Context Profiles
- [ ] Обновить [CLAUDE.md](CLAUDE.md) — таблица моделей и профилей
- [ ] Создать ADR: "Абстракция AI клиентов и Context Profiles"

---

### Фаза 4: Кэширование промежуточных результатов

**Структура кэша:**

```
archive/2025/01.09 ПШ/Video Title/
├── pipeline_results.json        # (существующий)
└── .cache/
    ├── manifest.json            # Версии и метаданные
    ├── transcription/v1.json
    ├── cleaning/v1.json
    ├── cleaning/v2.json         # Re-run с другой моделью
    └── ...
```

**Файлы для создания:**

```
backend/app/models/cache.py      # Pydantic модели: StageVersion, CacheManifest
backend/app/services/pipeline/stage_cache.py  # StageResultCache сервис
```

**API endpoints (обновление):**

```python
POST /api/step/clean             # Добавить: model override, cache support
POST /api/step/chunk             # Добавить: model override, cache support
POST /api/step/rerun             # НОВЫЙ: re-run любого шага
GET  /api/cache/{video_id}       # НОВЫЙ: информация о версиях
```

**Критические файлы:**
- [step_routes.py](backend/app/api/step_routes.py) — расширение endpoints
- [saver.py](backend/app/services/saver.py) — интеграция с кэшем

**Документация после Фазы 4:**
- [ ] Docstrings для `StageResultCache`, `CacheManifest`
- [ ] Обновить [api-reference.md](docs/api-reference.md) — новые endpoints
- [ ] Обновить [data-formats.md](docs/data-formats.md) — формат manifest.json
- [ ] Создать ADR: "Версионирование промежуточных результатов"

---

### Фаза 5: Реализация Claude API (после фаз 1-4)

**Задачи:**
1. Реализовать `ClaudeClient` в [claude_client.py](backend/app/services/ai_clients/claude_client.py)
2. Добавить `ProcessingStrategy` для выбора local/cloud обработки
3. Обновить сервисы для использования strategy pattern
4. Добавить UI для выбора модели

**Документация после Фазы 5:**
- [ ] Docstrings для `ClaudeClient`, `ProcessingStrategy`
- [ ] Обновить [configuration.md](docs/configuration.md) — настройка Claude API
- [ ] Обновить [CLAUDE.md](CLAUDE.md) — как использовать облачные модели
- [ ] Создать ADR: "Интеграция облачных моделей"

---

## Архитектурная диаграмма (целевая)

```
┌─────────────────────────────────────────────────────────────────┐
│                      PipelineOrchestrator                        │
│                    (координация этапов)                          │
└────────────┬───────────────────────────────────────────────────┘
             │
    ┌────────┼────────┬─────────────┬─────────────┐
    │        │        │             │             │
    ▼        ▼        ▼             ▼             ▼
Progress  Fallback  Config      Stage         AI Client
Manager   Factory   Resolver    Cache         Factory
    │                             │             │
    │                             │      ┌──────┼──────┐
    │                             │      ▼      ▼      ▼
    │                             │   Ollama  Claude  (future)
    │                             │   Client  Client
    │                             │
    └─────────────────────────────┴─────────────────────────────
                                  │
              ┌───────────────────┼───────────────────┐
              ▼                   ▼                   ▼
         Transcriber         Chunker            LongreadGen
         (Whisper)       (SemanticChunker)    (SummaryGen)
                               │
                    ┌──────────┼──────────┐
                    ▼          ▼          ▼
               json_utils  chunk_utils  token_utils
```

---

## Влияние на существующий код

| Компонент | Изменение | Breaking |
|-----------|-----------|----------|
| pipeline.py | Декомпозиция на модули | Нет |
| chunker.py | Объединение методов | Нет |
| ai_client.py | Переименование → OllamaClient | Да (internal) |
| step_routes.py | Новые параметры | Да |
| Frontend | Обновление API вызовов | Да |
| models.yaml | Расширение структуры | Нет |

---

## Порядок выполнения

```
Фаза 0 ──┐
         ├──→ Фаза 1 ──┐
         │             ├──→ Фаза 3 ──→ Фаза 4 ──→ Фаза 5
         └──→ Фаза 2 ──┘
```

0. **Фаза 0** — Stage абстракция (расширяемость для новых шагов)
1. **Фаза 1** — Декомпозиция pipeline.py
2. **Фаза 2** — Декомпозиция chunker.py + Context Profiles
3. **Фаза 3** — Абстракция AI клиентов
4. **Фаза 4** — Кэширование результатов
5. **Фаза 5** — Claude API (отдельная задача)

**Зависимости:**
- Фаза 0 делается первой (определяет структуру Stage)
- Фазы 1-2 можно делать параллельно после Фазы 0
- Фазы 3-4 зависят от 1-2

---

## Документация: ADR (Architecture Decision Records)

Для фиксации архитектурных решений создаём папку `docs/adr/`:

```
docs/adr/
├── 001-stage-abstraction.md         # Фаза 0: Почему Stage pattern
├── 002-pipeline-decomposition.md    # Фаза 1: Почему декомпозиция pipeline
├── 003-shared-utils.md              # Фаза 2: Почему shared utils
├── 004-ai-client-abstraction.md     # Фаза 3: Почему абстракция клиентов
├── 005-result-caching.md            # Фаза 4: Почему версионирование кэша
└── 006-cloud-models.md              # Фаза 5: Почему Claude API
```

**Формат ADR:**
```markdown
# ADR-001: Stage Abstraction

## Статус
Принято

## Контекст
Нужна возможность легко добавлять новые шаги обработки (Telegram Summary).

## Решение
Введение BaseStage, StageContext, StageRegistry.

## Последствия
+ Новые шаги добавляются без изменения orchestrator
+ Автоматический граф зависимостей
- Увеличение количества файлов
```

---

## Верификация

После каждой фазы:

1. **Unit-тесты**: Запустить существующие тесты
   ```bash
   python3 -m pytest backend/tests/ -v
   ```

2. **Integration test**: Прогнать полный pipeline на тестовом видео
   ```bash
   # На сервере через deploy
   ./scripts/deploy.sh
   # Проверить через UI: http://100.64.0.1:8802
   ```

3. **Step-by-step**: Проверить каждый endpoint отдельно
   ```bash
   curl -X POST http://100.64.0.1:8801/api/step/parse -d '{"video_path": "..."}'
   ```
