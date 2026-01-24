---
doc_type: adr
status: accepted
created: 2025-01-22
updated: 2026-01-24
audience: [developer]
tags:
  - architecture
  - adr
  - metrics
---

# ADR-009: Расширенные метрики обработки

## Статус

Принято (2025-01-22)

## Контекст

С переходом на облачные модели (ADR-006, ADR-007) появилась необходимость отслеживать:
1. **Стоимость обработки** — Claude API тарифицируется по токенам
2. **Качество транскрипции** — confidence от Whisper для оценки качества
3. **Производительность** — время выполнения каждого этапа

### Мотивация

- Пользователи хотят видеть, сколько стоила обработка видео
- Для отладки промптов полезно знать количество использованных токенов
- Метрики качества помогают выявлять проблемные транскрипции

## Решение

### 1. Унификация AI клиентов (v0.43)

Все AI клиенты возвращают `tuple[str, ChatUsage]`:

```python
# backend/app/services/ai_clients/base.py
@dataclass
class ChatUsage:
    """Token usage statistics from AI response."""
    input_tokens: int = 0
    output_tokens: int = 0

# Использование
async def chat(...) -> tuple[str, ChatUsage]:
    response = await self.client.messages.create(...)
    usage = ChatUsage(
        input_tokens=response.usage.input_tokens,
        output_tokens=response.usage.output_tokens,
    )
    return response.content[0].text, usage
```

### 2. TokensUsed в Pydantic моделях (v0.42)

```python
# backend/app/models/schemas.py
class TokensUsed(BaseModel):
    """Token usage statistics for LLM operations."""
    input: int
    output: int

    @computed_field
    @property
    def total(self) -> int:
        return self.input + self.output
```

### 3. Метрики в результатах этапов

Каждый LLM-этап возвращает расширенные метрики:

| Этап | Метрики |
|------|---------|
| Transcribe | `confidence`, `processing_time_sec`, `chars`, `words` |
| Clean | `tokens_used`, `cost`, `processing_time_sec`, `words`, `change_percent` |
| Longread | `tokens_used`, `cost`, `processing_time_sec`, `chars` |
| Summary | `tokens_used`, `cost`, `processing_time_sec`, `chars`, `words` |
| Story | `tokens_used`, `cost`, `processing_time_sec`, `chars` |
| Chunk | `total_tokens` |

### 4. Pricing в models.yaml (v0.42)

```yaml
claude_models:
  - id: "claude-sonnet-4-5"
    pricing:
      input: 3.00   # $ за 1M токенов
      output: 15.00
```

### 5. Утилиты расчёта стоимости

```python
# backend/app/utils/pricing_utils.py
def calculate_cost(model_id: str, input_tokens: int, output_tokens: int) -> float:
    """Calculate cost in USD based on model pricing."""
    pricing = get_model_pricing(model_id)
    if not pricing:
        return 0.0  # Free for local models
    return (
        input_tokens / 1_000_000 * pricing.input +
        output_tokens / 1_000_000 * pricing.output
    )
```

### 6. Frontend компоненты (v0.44-v0.46)

**Утилиты форматирования:**
```typescript
// frontend/src/utils/formatUtils.ts
formatTime(6.2)        // → "6с"
formatTime(125.5)      // → "2м 6с"
formatCost(0.0314)     // → "~$0.03"
formatCost(0)          // → "бесплатно"
formatTokens(3570)     // → "3 570"
```

**Компоненты отображения:**
- `ResultFooter.tsx` — показывает метрики внизу карточки результата
- `InlineDiffView.tsx` — показывает diff изменений

## Последствия

### Положительные

- Прозрачность затрат на обработку
- Возможность отладки и оптимизации промптов
- Выявление проблемных транскрипций по low confidence
- Единый интерфейс для всех AI клиентов

### Нейтральные

- Локальные модели (Ollama) показывают cost = 0 (бесплатно)
- Whisper не возвращает token usage (только confidence)

### Отрицательные

- Небольшое увеличение размера API responses
- Дополнительная логика в генераторах для сбора метрик

## Связанные решения

- [ADR-004: AI Client Abstraction](004-ai-client-abstraction.md) — базовая архитектура клиентов
- [ADR-006: Cloud Model Integration](006-cloud-model-integration.md) — интеграция Claude
- [ADR-007: Remove Fallback](007-remove-fallback-use-claude.md) — Claude как основной провайдер
