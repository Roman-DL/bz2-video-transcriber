# Рефакторинг: Унификация интерфейса AI клиентов

**Цель:** Убрать дублирование кода и `isinstance()` проверки. Единый интерфейс для всех AI клиентов.

---

## Суть изменения

**Было:**
```python
# В каждом сервисе
if isinstance(self.ai_client, ClaudeClient):
    response, usage = await self.ai_client.chat_with_usage(...)
else:
    response = await self.ai_client.chat(...)
```

**Станет:**
```python
# Везде одинаково
response, usage = await self.ai_client.chat(...)
# OllamaClient возвращает ChatUsage(0, 0) — честно отражает отсутствие tracking
```

---

## Файлы для изменения (8 файлов)

### 1. backend/app/services/ai_clients/base.py

**Добавить `ChatUsage` dataclass:**
```python
@dataclass
class ChatUsage:
    """Token usage from AI API response."""
    input_tokens: int = 0
    output_tokens: int = 0

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens
```

**Изменить сигнатуры в Protocol и BaseAIClientImpl:**
```python
async def chat(...) -> tuple[str, ChatUsage]    # было -> str
async def generate(...) -> tuple[str, ChatUsage]  # было -> str
```

---

### 2. backend/app/services/ai_clients/claude_client.py

- Удалить локальный `ChatUsage` — импорт из base.py
- Удалить старые методы `chat()` и `generate()` (возвращавшие `str`)
- Переименовать `chat_with_usage()` → `chat()`
- Переименовать `generate_with_usage()` → `generate()`

---

### 3. backend/app/services/ai_clients/ollama_client.py

- Импортировать `ChatUsage` из base.py
- Изменить `generate()`: `return response_text, ChatUsage()`
- Изменить `chat()`: `return content, ChatUsage()`

---

### 4. backend/app/services/ai_clients/__init__.py

- Изменить импорт `ChatUsage` с `claude_client` на `base`

---

### 5. backend/app/services/cleaner.py

- Убрать `ClaudeClient` из импортов
- Удалить `has_usage_tracking = isinstance(...)`
- Упростить цикл — всегда использовать tuple return:
```python
chunk_result, usage = await self.ai_client.chat(...)
total_input_tokens += usage.input_tokens
```

---

### 6. backend/app/services/longread_generator.py

- Убрать `ClaudeClient` из импортов
- Удалить `self._has_usage_tracking` из `__init__`
- Упростить `_generate_section()` и `_generate_frame()`:
```python
response, usage = await self.ai_client.generate(...)
async with self._tokens_lock:
    self._total_input_tokens += usage.input_tokens
```

---

### 7. backend/app/services/summary_generator.py

- Убрать `ClaudeClient` из импортов
- Удалить `has_usage_tracking = isinstance(...)`
- Упростить вызов:
```python
response, usage = await self.ai_client.generate(...)
input_tokens = usage.input_tokens
```

---

### 8. backend/app/services/story_generator.py

- Убрать `ClaudeClient` из импортов
- Удалить `has_usage_tracking = isinstance(...)`
- Упростить вызов (аналогично summary_generator)

---

## Порядок выполнения

1. `base.py` — добавить ChatUsage, изменить Protocol
2. `claude_client.py` — удалить старые методы
3. `ollama_client.py` — добавить ChatUsage в return
4. `__init__.py` — обновить экспорт
5. `cleaner.py` → `longread_generator.py` → `summary_generator.py` → `story_generator.py`

---

## Верификация

```bash
cd backend
source .venv/bin/activate

# 1. Проверка синтаксиса
python3 -m py_compile app/services/ai_clients/base.py
python3 -m py_compile app/services/ai_clients/claude_client.py
python3 -m py_compile app/services/ai_clients/ollama_client.py
python3 -m py_compile app/services/cleaner.py

# 2. Встроенные тесты (без реальных API)
python -m app.services.ai_clients.base

# 3. Деплой и тест на сервере
./scripts/deploy.sh
# Затем: обработать тестовое видео через UI
```

---

## Результат

- ~50 строк кода удалено (условные проверки)
- Единый интерфейс BaseAIClient
- Чистая архитектура без isinstance() хаков
