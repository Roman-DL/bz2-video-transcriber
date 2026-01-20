# ADR-004: Абстракция AI клиентов и Context Profiles

## Статус

Принято (2025-01-20)

## Контекст

Система изначально была разработана только для локальных моделей через Ollama API. При планировании поддержки облачных моделей (Claude API) выявились проблемы:

1. **Жёсткая привязка к Ollama** — класс `AIClient` содержал специфичную логику Ollama API
2. **Дублирование параметров** — каждая модель в `models.yaml` полностью определяла все параметры обработки
3. **Отсутствие абстракции** — невозможно добавить новый провайдер без изменения множества сервисов

### Проблема дублирования параметров

До рефакторинга в `models.yaml`:

```yaml
models:
  gemma2:
    context_tokens: 8192
    cleaner:
      chunk_size: 3000
      chunk_overlap: 200
      # ... 10+ параметров
  qwen2:
    context_tokens: 32768
    cleaner:
      chunk_size: 8000
      chunk_overlap: 500
      # ... те же 10+ параметров
```

При добавлении Claude нужно было бы копировать все параметры, что нарушает DRY.

## Решение

### 1. Абстракция AI клиентов

Создать пакет `backend/app/services/ai_clients/`:

```
backend/app/services/ai_clients/
├── __init__.py          # Экспорт публичных классов
├── base.py              # BaseAIClient (Protocol), AIClientConfig, исключения
├── ollama_client.py     # OllamaClient — реализация для Ollama + Whisper
└── claude_client.py     # ClaudeClient — заглушка для Phase 5
```

#### BaseAIClient Protocol

```python
@runtime_checkable
class BaseAIClient(Protocol):
    """Интерфейс для всех AI клиентов."""

    async def generate(
        self,
        prompt: str,
        model: str | None = None,
        num_predict: int | None = None,
    ) -> str: ...

    async def chat(
        self,
        messages: list[dict],
        model: str | None = None,
        temperature: float = 0.7,
        num_predict: int | None = None,
    ) -> str: ...

    async def close(self) -> None: ...
```

Protocol (а не ABC) позволяет типизировать любой объект с нужными методами.

#### Иерархия исключений

```python
AIClientError                    # Базовое исключение
├── AIClientTimeoutError         # Таймаут запроса
├── AIClientConnectionError      # Ошибка соединения
└── AIClientResponseError        # Ошибка от API (4xx, 5xx)
```

### 2. Context Profiles

Вместо дублирования параметров — профили размера контекста:

```yaml
context_profiles:
  small:    # < 16K tokens (gemma2:9b)
    chunk_size: 3000
    large_text_threshold: 10000
    # ...

  medium:   # 16K - 64K tokens (qwen2.5:14b)
    chunk_size: 8000
    large_text_threshold: 25000
    # ...

  large:    # > 100K tokens (Claude)
    chunk_size: 100000
    large_text_threshold: 200000
    # ...

models:
  gemma2:
    provider: ollama
    context_profile: small  # Параметры из профиля
    context_tokens: 8192

  claude-sonnet:
    provider: claude
    context_profile: large  # Параметры из профиля
    context_tokens: 200000
```

Преимущества:
- **DRY** — параметры определяются один раз
- **Понятная логика** — размер контекста → профиль → параметры
- **Гибкость** — можно override отдельные параметры для модели

### 3. Providers

Конфигурация провайдеров AI:

```yaml
providers:
  ollama:
    type: "local"
    default_profile: small
    base_url_env: "OLLAMA_URL"

  claude:
    type: "cloud"
    default_profile: large
    api_key_env: "ANTHROPIC_API_KEY"
```

## Миграция

### Изменения в коде

1. **Удалён** `backend/app/services/ai_client.py`
2. **Создан** пакет `backend/app/services/ai_clients/`
3. **Обновлены импорты** во всех сервисах:
   ```python
   # Было
   from app.services.ai_client import AIClient
   async with AIClient(settings) as client:

   # Стало
   from app.services.ai_clients import OllamaClient
   async with OllamaClient.from_settings(settings) as client:
   ```

### Затронутые файлы

- `backend/app/main.py`
- `backend/app/services/pipeline/orchestrator.py`
- `backend/app/services/transcriber.py`
- `backend/app/services/cleaner.py`
- `backend/app/services/chunker.py`
- `backend/app/services/summarizer.py`
- `backend/app/services/longread_generator.py`
- `backend/app/services/summary_generator.py`
- `backend/app/services/outline_extractor.py`
- `backend/app/services/stages/*.py`
- `config/models.yaml`

## Последствия

### Положительные

- **Расширяемость** — легко добавить новые AI провайдеры
- **DRY** — параметры не дублируются между моделями
- **Типизация** — Protocol обеспечивает статическую проверку
- **Тестируемость** — можно создать mock-клиент для тестов
- **Изоляция** — изменения в API Ollama не затрагивают сервисы

### Отрицательные

- **Увеличение кода** — новый пакет с несколькими файлами
- **Breaking change** — все импорты нужно обновить
- **Сложность** — нужно понимать систему профилей

### Не реализовано (Phase 5)

- Полная реализация `ClaudeClient`
- Автоматический выбор провайдера по модели
- Fallback между провайдерами

## Связанные документы

- [ADR-001: Stage Abstraction](001-stage-abstraction.md)
- [ADR-002: Pipeline Decomposition](002-pipeline-decomposition.md)
- [ADR-003: Shared Utils](003-shared-utils.md)
- [docs/configuration.md](../configuration.md) — описание Context Profiles
