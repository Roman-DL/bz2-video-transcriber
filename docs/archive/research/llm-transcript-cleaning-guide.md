# Выбор LLM для очистки транскриптов

## Проблема

При очистке транскриптов от слов-паразитов модель `qwen2.5:14b` демонстрирует нежелательное поведение:

| Размер текста | Reduction | Поведение |
|---------------|-----------|-----------|
| < 2 KB | ~15-20% | ✅ Корректная очистка |
| 8+ KB | 68-90% | ❌ Суммаризация вместо очистки |

**Причина:** На длинных текстах модель "переключается" в режим суммаризации, игнорируя инструкции сохранять весь контент.

---

## Установленные модели

Ollama API: `http://100.64.0.1:11434`

| Модель | Размер | VRAM | Особенности |
|--------|--------|------|-------------|
| `qwen2.5:14b` | 9.0 GB | ~9 GB | Отличный русский, но суммаризирует длинные тексты |
| `qwen2.5:7b` | 4.7 GB | ~5 GB | Быстрее, те же проблемы |
| `gemma2:9b` | 5.4 GB | ~6 GB | **Рекомендуется** — минимум "креатива", следует инструкциям |
| `mistral:7b-instruct` | 4.4 GB | ~5 GB | Жёсткое следование инструкциям |
| `phi3:14b` | 7.9 GB | ~8 GB | Microsoft, оптимизирована для конкретных задач |

---

## Методология тестирования

### Метрики качества

```python
def evaluate_cleaning(original: str, cleaned: str) -> dict:
    """Оценка качества очистки."""
    original_len = len(original)
    cleaned_len = len(cleaned)
    reduction = 1 - (cleaned_len / original_len)
    
    return {
        "original_chars": original_len,
        "cleaned_chars": cleaned_len,
        "reduction_percent": round(reduction * 100, 1),
        "is_acceptable": 5 <= reduction * 100 <= 25,  # 5-25% — нормальная очистка
    }
```

### Критерии оценки

| Reduction | Интерпретация |
|-----------|---------------|
| < 5% | Слишком мало удалено (не работает) |
| 5-15% | ✅ Идеальная очистка |
| 15-25% | ✅ Приемлемо (много паразитов в исходнике) |
| 25-40% | ⚠️ Подозрительно — проверить вручную |
| > 40% | ❌ Суммаризация — модель не подходит |

### Тестовые файлы

Для корректного тестирования нужны файлы разных размеров:

| Файл | Размер | Назначение |
|------|--------|------------|
| `test_small.txt` | ~1-2 KB | Базовый тест |
| `test_medium.txt` | ~4-5 KB | Пограничный случай |
| `test_large.txt` | ~8-10 KB | Проверка на суммаризацию |
| `test_xlarge.txt` | ~15-20 KB | Стресс-тест |

---

## Код для тестирования

### Базовый тест модели

```python
import requests
from typing import Optional

OLLAMA_HOST = "http://100.64.0.1:11434"

def clean_with_model(
    text: str,
    model: str,
    system_prompt: str,
    temperature: float = 0
) -> str:
    """Очистить текст указанной моделью."""
    response = requests.post(
        f"{OLLAMA_HOST}/api/generate",
        json={
            "model": model,
            "prompt": f"<input>\n{text}\n</input>",
            "system": system_prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
            }
        },
        timeout=300
    )
    response.raise_for_status()
    return response.json()["response"]


def test_model(model: str, text: str, system_prompt: str) -> dict:
    """Тестировать модель и вернуть метрики."""
    import time
    
    start = time.time()
    cleaned = clean_with_model(text, model, system_prompt)
    elapsed = time.time() - start
    
    original_len = len(text)
    cleaned_len = len(cleaned)
    reduction = 1 - (cleaned_len / original_len)
    
    return {
        "model": model,
        "original_chars": original_len,
        "cleaned_chars": cleaned_len,
        "reduction_percent": round(reduction * 100, 1),
        "time_seconds": round(elapsed, 1),
        "is_acceptable": 5 <= reduction * 100 <= 25,
        "cleaned_text": cleaned[:500] + "..." if len(cleaned) > 500 else cleaned,
    }
```

### Сравнительный тест всех моделей

```python
MODELS = [
    "qwen2.5:14b",
    "qwen2.5:7b",
    "gemma2:9b",
    "mistral:7b-instruct",
    "phi3:14b",
]

SYSTEM_PROMPT = """Ты — технический редактор. Твоя единственная задача: удалить слова-паразиты из текста, сохранив ВСЁ остальное.

## УДАЛЯЙ ТОЛЬКО:
- Слова-паразиты: "ну", "вот", "как бы", "типа", "короче", "значит", "так сказать", "в общем", "собственно"
- Заполнители пауз: "э-э-э", "м-м-м", "а-а-а"
- Технические фразы: "вы меня слышите?", "видно экран?", "подождите секунду"

## КРИТИЧЕСКИ ВАЖНО:
1. Выходной текст должен быть 85-95% от входного
2. НЕ сокращай, НЕ пересказывай, НЕ делай саммари
3. НЕ добавляй заголовки
4. Каждое предложение из входа должно быть в выходе (без паразитов)

## ФОРМАТ ОТВЕТА:
Выведи ТОЛЬКО отредактированный текст. Без комментариев, без заголовков.
"""


def compare_models(test_file: str) -> list[dict]:
    """Сравнить все модели на одном файле."""
    with open(test_file, "r") as f:
        text = f.read()
    
    results = []
    for model in MODELS:
        print(f"Testing {model}...")
        try:
            result = test_model(model, text, SYSTEM_PROMPT)
            results.append(result)
            print(f"  → {result['reduction_percent']}% reduction in {result['time_seconds']}s")
        except Exception as e:
            print(f"  → ERROR: {e}")
            results.append({"model": model, "error": str(e)})
    
    return results


def print_comparison_table(results: list[dict]):
    """Вывести таблицу сравнения."""
    print("\n" + "=" * 70)
    print(f"{'Model':<25} {'Reduction':<12} {'Time':<10} {'Status':<15}")
    print("=" * 70)
    
    for r in results:
        if "error" in r:
            print(f"{r['model']:<25} {'ERROR':<12} {'-':<10} {r['error'][:15]}")
        else:
            status = "✅ OK" if r["is_acceptable"] else "❌ FAIL"
            print(f"{r['model']:<25} {r['reduction_percent']:>5}%      {r['time_seconds']:>5}s     {status}")
    
    print("=" * 70)
```

### Запуск теста

```python
# Тест на разных размерах
for test_file in ["test_small.txt", "test_medium.txt", "test_large.txt"]:
    print(f"\n\n{'='*70}")
    print(f"FILE: {test_file}")
    print(f"{'='*70}")
    results = compare_models(test_file)
    print_comparison_table(results)
```

---

## Стратегия чанкинга

Если модель суммаризирует длинные тексты — разбивай на чанки:

```python
import re

def clean_in_chunks(
    text: str,
    model: str,
    system_prompt: str,
    chunk_size: int = 2500
) -> str:
    """Очистка текста чанками."""
    # Разбить по предложениям
    sentences = re.split(r'(?<=[.!?])\s+', text)
    
    chunks = []
    current_chunk = []
    current_size = 0
    
    for sentence in sentences:
        if current_size + len(sentence) > chunk_size and current_chunk:
            chunks.append(' '.join(current_chunk))
            current_chunk = [sentence]
            current_size = len(sentence)
        else:
            current_chunk.append(sentence)
            current_size += len(sentence)
    
    if current_chunk:
        chunks.append(' '.join(current_chunk))
    
    # Очистить каждый чанк
    cleaned_chunks = []
    for i, chunk in enumerate(chunks):
        print(f"  Processing chunk {i+1}/{len(chunks)} ({len(chunk)} chars)...")
        cleaned = clean_with_model(chunk, model, system_prompt)
        cleaned_chunks.append(cleaned)
    
    return '\n\n'.join(cleaned_chunks)
```

### Выбор размера чанка

| Модель | Рекомендуемый chunk_size |
|--------|--------------------------|
| `qwen2.5:14b` | 2000-2500 chars |
| `qwen2.5:7b` | 2000-2500 chars |
| `gemma2:9b` | 3000-4000 chars (более стабильна) |
| `mistral:7b-instruct` | 3000-4000 chars |
| `phi3:14b` | 2500-3500 chars |

---

## Оптимизация промпта

### Усиленный промпт для длинных текстов

```python
ENHANCED_SYSTEM_PROMPT = """Ты — технический редактор. Твоя ЕДИНСТВЕННАЯ задача: удалить слова-паразиты.

## ПРАВИЛА:
1. СОХРАНИ каждое предложение из входного текста
2. УДАЛИ только: ну, вот, как бы, типа, короче, значит, э-э-э, м-м-м
3. НЕ СОКРАЩАЙ текст
4. НЕ СУММАРИЗИРУЙ
5. НЕ ПЕРЕФРАЗИРУЙ

## САМОПРОВЕРКА:
- Входной текст содержит N предложений
- Выходной текст ДОЛЖЕН содержать N предложений
- Если выход короче 80% входа — ты делаешь ошибку

## ПРИМЕР:
Вход: "Ну вот, значит, мы решили, как бы, сделать это так."
Выход: "Мы решили сделать это так."

## ФОРМАТ:
Выведи ТОЛЬКО очищенный текст. Без комментариев."""


ENHANCED_USER_PROMPT = """<input>
{text}
</input>

НАПОМИНАНИЕ: Выведи весь текст, удалив только слова-паразиты. Длина вывода ≈ 85-95% от ввода."""
```

### Few-shot примеры

```python
FEW_SHOT_EXAMPLES = """
## ПРИМЕРЫ ПРАВИЛЬНОЙ ОЧИСТКИ:

Вход: "Ну вот, значит, погода сегодня, как бы, хорошая, да."
Выход: "Погода сегодня хорошая."

Вход: "Э-э-э, мы, типа, пошли в магазин, ну, купили там хлеб и молоко."
Выход: "Мы пошли в магазин, купили там хлеб и молоко."

Вход: "Так сказать, в общем, компания работает уже, короче, десять лет на рынке."
Выход: "Компания работает уже десять лет на рынке."
"""
```

---

## Рекомендации

### Для продакшена

1. **Начни с `gemma2:9b`** — она наиболее стабильна для задач очистки
2. **Используй чанкинг** — 2500-3000 символов на чанк
3. **Валидируй результат** — если reduction > 30%, перезапусти с меньшим чанком
4. **Логируй метрики** — для мониторинга качества

### Fallback стратегия

```python
def clean_with_fallback(text: str, system_prompt: str) -> str:
    """Очистка с автоматическим fallback."""
    
    # Попытка 1: gemma2 целиком (если текст небольшой)
    if len(text) < 3000:
        result = clean_with_model(text, "gemma2:9b", system_prompt)
        reduction = 1 - len(result) / len(text)
        if reduction < 0.30:
            return result
    
    # Попытка 2: gemma2 с чанкингом
    result = clean_in_chunks(text, "gemma2:9b", system_prompt, chunk_size=2500)
    reduction = 1 - len(result) / len(text)
    if reduction < 0.30:
        return result
    
    # Попытка 3: mistral с мелким чанкингом
    result = clean_in_chunks(text, "mistral:7b-instruct", system_prompt, chunk_size=1500)
    return result
```

---

## API Reference

### Ollama Generate

```bash
curl -X POST http://100.64.0.1:11434/api/generate \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gemma2:9b",
    "prompt": "<input>\n...\n</input>",
    "system": "...",
    "stream": false,
    "options": {
      "temperature": 0
    }
  }'
```

### Ollama Chat (OpenAI-compatible)

```bash
curl -X POST http://100.64.0.1:11434/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gemma2:9b",
    "messages": [
      {"role": "system", "content": "..."},
      {"role": "user", "content": "<input>...</input>"}
    ],
    "temperature": 0
  }'
```

### Проверка моделей

```bash
curl -s http://100.64.0.1:11434/api/tags | jq '.models[].name'
```

---

## Чеклист перед использованием

- [ ] Ollama доступен: `curl http://100.64.0.1:11434/api/version`
- [ ] Модели установлены: `curl http://100.64.0.1:11434/api/tags`
- [ ] Тестовые файлы подготовлены (разные размеры)
- [ ] Промпт оптимизирован под задачу
- [ ] Метрики качества определены
- [ ] Fallback стратегия реализована

---

## История изменений

| Дата | Изменение |
|------|-----------|
| 2025-01-11 | Документ создан |
| 2025-01-11 | Добавлены модели: gemma2:9b, mistral:7b-instruct, phi3:14b |
