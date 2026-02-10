---
doc_type: adr
status: accepted
created: 2025-01-20
updated: 2026-01-24
audience: [developer]
tags:
  - architecture
  - adr
  - llm
  - api
---

# ADR-006: Интеграция облачных моделей (Claude API)

## Статус

Принято (2025-01-20)

> **Примечание v0.27:** ProcessingStrategy управляет только LLM клиентами (OllamaClient, ClaudeClient). Транскрибация выделена в отдельный WhisperClient (см. ADR-004).

## Контекст

В ADR-004 была создана абстракция AI клиентов с заглушкой для Claude API. Phase 5 реализует полную интеграцию Claude API для обработки длинных документов без необходимости чанкирования.

### Мотивация

1. **Большой контекст** — Claude поддерживает 200K токенов, что позволяет обрабатывать длинные транскрипты целиком
2. **Качество** — облачные модели показывают лучшее качество на сложных задачах
3. **Гибкость** — возможность выбора между скоростью (local) и качеством (cloud)

### Ограничения локальных моделей

| Модель | Context | Ограничение |
|--------|---------|-------------|
| gemma2:9b | 8K | Требует агрессивного чанкирования |
| qwen2.5:14b | 32K | Достаточно для большинства видео |
| Claude | 200K | Любой транскрипт целиком |

## Решение

### 1. Реализация ClaudeClient

Полная реализация `ClaudeClient` с использованием официального Anthropic SDK:

```python
from anthropic import AsyncAnthropic

class ClaudeClient(BaseAIClientImpl):
    """Async client for Anthropic's Claude API."""

    def __init__(self, config: AIClientConfig):
        self.client = AsyncAnthropic(
            api_key=config.api_key,
            timeout=config.timeout,
            max_retries=config.max_retries,
        )

    async def chat(self, messages: list[dict], ...) -> str:
        # Конвертация system message в параметр
        response = await self.client.messages.create(
            model=model,
            messages=chat_messages,
            system=system_content,
            max_tokens=num_predict,
        )
        return response.content[0].text
```

Ключевые особенности:
- **Конвертация формата** — Ollama-style messages → Claude format
- **System message** — выносится в отдельный параметр `system`
- **Cost logging** — логирование input/output токенов для мониторинга расходов
- **Retry logic** — встроенный retry в Anthropic SDK

### 2. ProcessingStrategy

Новый компонент для выбора провайдера на основе модели:

```python
class ProcessingStrategy:
    """Strategy for selecting AI providers."""

    CLOUD_MODEL_PREFIXES = ("claude",)

    def get_provider_type(self, model: str) -> ProviderType:
        """Determine provider type for a model."""
        if model.lower().startswith("claude"):
            return ProviderType.CLOUD
        return ProviderType.LOCAL

    def create_client(self, model: str) -> AsyncContextManager[BaseAIClient]:
        """Create appropriate AI client."""
        if self.get_provider_type(model) == ProviderType.CLOUD:
            return ClaudeClient.from_settings(self.settings)
        return OllamaClient.from_settings(self.settings)
```

#### Fallback механизм

```python
async def get_client_with_fallback(
    self,
    preferred_model: str,
    fallback_model: str,
) -> tuple[BaseAIClient, str]:
    """
    Get client with automatic fallback.

    Example:
        client, model = await strategy.get_client_with_fallback(
            "claude-sonnet", "qwen2.5:14b"
        )
    """
    try:
        # Try preferred (cloud)
        client = ClaudeClient.from_settings(self.settings)
        await client.check_api_key()
        return client, preferred_model
    except (ValueError, AIClientConnectionError):
        # Fallback to local
        return OllamaClient.from_settings(self.settings), fallback_model
```

### 3. Конфигурация

#### Переменные окружения

```bash
# docker-compose.yml
ANTHROPIC_API_KEY=sk-ant-...  # Обязательно для Claude
```

#### models.yaml

Модель уже настроена в Phase 3:

```yaml
models:
  claude-sonnet:
    provider: claude
    context_profile: large
    context_tokens: 200000
```

## Архитектура

```
┌─────────────────────────────────────────────────────────────┐
│                    ProcessingStrategy                        │
│  ┌─────────────────┐                 ┌─────────────────┐   │
│  │  ProviderType   │                 │  ProviderInfo   │   │
│  │  - LOCAL        │                 │  - type         │   │
│  │  - CLOUD        │                 │  - name         │   │
│  └────────┬────────┘                 │  - available    │   │
│           │                          └─────────────────┘   │
│           ▼                                                 │
│  ┌─────────────────────────────────────────────────────┐   │
│  │           get_provider_type(model)                   │   │
│  │  "claude-*"  → CLOUD  │  other → LOCAL               │   │
│  └─────────────────────────────────────────────────────┘   │
│                          │                                  │
│           ┌──────────────┴──────────────┐                  │
│           ▼                              ▼                  │
│  ┌─────────────────┐            ┌─────────────────┐        │
│  │  ClaudeClient   │            │  OllamaClient   │        │
│  │  - Anthropic SDK│            │  - httpx        │        │
│  │  - 200K context │            │  - Whisper      │        │
│  └─────────────────┘            └─────────────────┘        │
└─────────────────────────────────────────────────────────────┘
```

## Использование

### Прямое создание клиента

```python
from app.services.ai_clients import ClaudeClient

async with ClaudeClient.from_settings(settings) as client:
    response = await client.generate("Analyze this text...")
```

### Через ProcessingStrategy

```python
from app.services.pipeline import ProcessingStrategy

strategy = ProcessingStrategy(settings)

# По имени модели (алиас)
async with strategy.create_client("claude-sonnet-4-5") as client:
    response = await client.generate("...")

# С fallback
client, model = await strategy.get_client_with_fallback(
    "claude-sonnet-4-5", "qwen2.5:14b"
)
```

## Миграция

### Новые зависимости

```bash
# backend/requirements.txt
anthropic>=0.40.0
```

### Структура файлов

```
backend/app/services/
├── ai_clients/
│   ├── __init__.py         # Обновлён: экспорт ClaudeClient
│   ├── base.py             # Без изменений
│   ├── ollama_client.py    # Без изменений
│   └── claude_client.py    # Реализован (был заглушкой)
└── pipeline/
    ├── __init__.py         # Обновлён: экспорт ProcessingStrategy
    ├── processing_strategy.py  # Новый
    └── ...
```

## Последствия

### Положительные

- **Большой контекст** — документы до 200K токенов без чанкирования
- **Качество** — лучшие результаты на сложных задачах
- **Гибкость** — выбор между local/cloud на уровне конфигурации
- **Fallback** — автоматическое переключение при недоступности

### Отрицательные

- **Стоимость** — Claude API платный ($3/1M input, $15/1M output для Sonnet)
- **Зависимость от сети** — cloud требует интернет
- **Задержка** — сетевые запросы медленнее локальных

### Мониторинг расходов

ClaudeClient логирует использование токенов:

```
2025-01-20 10:30:15 | INFO | Claude response: 5432 chars, tokens: 12500 in / 1500 out
```

При $3/1M input и $15/1M output Sonnet:
- 12500 input = $0.0375
- 1500 output = $0.0225
- Итого: ~$0.06 за запрос

## Связанные документы

- [ADR-004: AI Client Abstraction](004-ai-client-abstraction.md) — базовая абстракция
- [docs/configuration.md](../configuration.md) — настройка моделей
