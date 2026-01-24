---
doc_type: adr
status: accepted
created: 2026-01-21
updated: 2026-01-24
audience: [developer]
tags:
  - architecture
  - adr
  - llm
---

# ADR-007: Удаление Fallback механизмов и переход на Claude по умолчанию

**Статус:** Принято
**Дата:** 2026-01-21
**Версия:** v0.29

## Контекст

Система имела fallback механизмы, которые при ошибках LLM генерации (longread, summary) возвращали минимальные/пустые результаты вместо ошибок. Это скрывало проблемы и приводило к непредсказуемому качеству выходных документов.

Кроме того, defaults были настроены на локальные модели (gemma2:9b, qwen2.5:14b), хотя Claude Sonnet обеспечивает значительно лучшее качество для задач генерации текста.

## Решение

### 1. Удаление Fallback

**Удалённые компоненты:**
- `backend/app/services/pipeline/fallback_factory.py` — полностью удалён
- `FallbackFactory` — убран из экспорта `pipeline/__init__.py`
- `get_client_with_fallback()` — удалён из `ProcessingStrategy`

**Изменённое поведение:**
- При ошибке LLM генерации теперь выбрасывается `PipelineError`
- Пользователь видит чёткое сообщение об ошибке
- Нет "молчаливых" деградаций качества

**Изменённые файлы:**
- `orchestrator.py` — убраны try/except с fallback
- `longread_stage.py` — убран метод `_create_fallback_longread`
- `summarize_stage.py` — убран метод `_create_fallback_summary`
- `processing_strategy.py` — удалён `get_client_with_fallback()`

### 2. Claude Sonnet по умолчанию

**Изменённые defaults:**

| Параметр | Было | Стало |
|----------|------|-------|
| `CLEANER_MODEL` | gemma2:9b | claude-sonnet-4-5 |
| `LONGREAD_MODEL` | qwen2.5:14b | claude-sonnet-4-5 |
| `SUMMARIZER_MODEL` | qwen2.5:14b | claude-sonnet-4-5 |

**Требования:**
- Переменная `ANTHROPIC_API_KEY` должна быть установлена
- Прокси должен быть настроен (`HTTP_PROXY`, `HTTPS_PROXY`)

### 3. Отдельный селектор Longread

В форме настроек добавлен 4-й селектор "Лонгрид" для независимого выбора модели longread генерации.

**API изменения:**
- `/api/models/default` теперь возвращает `longread` поле
- `ModelSettings` во frontend включает `longread?: string`

## Последствия

### Преимущества

1. **Явные ошибки** — проблемы сразу видны, а не скрыты за "fallback"
2. **Лучшее качество** — Claude Sonnet существенно превосходит локальные модели
3. **Гибкость** — можно независимо настроить модель для каждого этапа
4. **Простота кода** — удалено ~200 строк fallback логики

### Недостатки

1. **Зависимость от Claude API** — требуется API ключ и доступ к сервису
2. **Стоимость** — использование Claude API платное
3. **Сетевая зависимость** — нужен стабильный интернет (через прокси)

## Миграция

При обновлении до v0.29:

1. Убедитесь, что `ANTHROPIC_API_KEY` установлен
2. Проверьте настройки прокси
3. При необходимости переопределите модели в docker-compose.yml:

```yaml
environment:
  - CLEANER_MODEL=gemma2:9b      # Вернуть локальную
  - LONGREAD_MODEL=qwen2.5:14b   # Вернуть локальную
  - SUMMARIZER_MODEL=qwen2.5:14b # Вернуть локальную
```

## Связанные документы

- [ADR-004: AI Client Abstraction](004-ai-client-abstraction.md)
- [ADR-006: Cloud Model Integration](006-cloud-model-integration.md)
- [Configuration Guide](../configuration.md)
