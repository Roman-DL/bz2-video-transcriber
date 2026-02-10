---
globs: backend/app/services/ai_clients/**,backend/app/services/cleaner.py,*_generator.py,slides_extractor.py
---

# Rules: AI Clients & Services

## BaseAIClient Protocol
- ВСЕГДА использовать async context manager для создания клиентов:
  ```python
  async with ClaudeClient.from_settings(settings) as client:
      response = await client.generate("...")
  ```
- НЕ создавать клиенты без контекстного менеджера

## ProcessingStrategy
- Автоматический выбор провайдера по имени модели:
  ```python
  async with strategy.create_client("claude-sonnet-4-5") as client: ...
  ```
- НИКОГДА не добавлять fallback между провайдерами (ADR-007)
- `get_client_with_fallback()` удалён — ошибки пробрасываются вызывающему коду

## Default Models (v0.29+)
- Очистка: `claude-sonnet-4-5`
- Слайды: `claude-haiku-4-5` (быстро и дёшево)
- Лонгрид: `claude-sonnet-4-5`
- Конспект: `claude-sonnet-4-5`
- Чанкирование: детерминистический (H2 парсинг), без LLM
- По умолчанию ВСЕ LLM операции — Claude. Требуется `ANTHROPIC_API_KEY`

## Context Profiles (config/models.yaml)
- `small` — gemma2:9b (< 16K tokens)
- `medium` — qwen2.5:14b (16K-64K tokens)
- `large` — Claude (> 100K tokens)

## Pricing
- Цены моделей: `config/models.yaml` → `claude_models[].pricing`
- Расчёт: `pricing_utils.calculate_cost(model_id, input_tokens, output_tokens)`
- Локальные модели (Ollama) — бесплатны, pricing не указывается
