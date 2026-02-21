---
doc_type: reference
status: active
updated: 2026-02-21
audience: [developer, ai-agent]
tags:
  - pipeline
  - stage
---

# Этап 3: Clean (Очистка транскрипта)

[< Назад: Transcribe](02-transcribe.md) | [Обзор Pipeline](README.md) | [Далее: Chunk >](04-chunk.md)

---

## Назначение

Нормализация терминологии в сыром транскрипте с использованием LLM и глоссария (v0.72+: только глоссарная подстановка).

## Input / Output

| Направление | Тип | Описание |
|-------------|-----|----------|
| **Input** | `parse: VideoMetadata` | Метаданные из этапа parse |
| | `transcribe: tuple[RawTranscript, Path]` | Транскрипт и аудио из этапа transcribe |
| **Output** | `CleanedTranscript` | Очищенный транскрипт с метриками |

**Зависимости:** `depends_on = ["parse", "transcribe"]`

### Поля CleanedTranscript

| Поле | Тип | Описание |
|------|-----|----------|
| `text` | `str` | Очищенный текст |
| `original_length` | `int` | Длина до очистки (символы) |
| `cleaned_length` | `int` | Длина после очистки (символы) |
| `model_name` | `str` | Использованная модель |
| `tokens_used` | `TokensUsed \| None` | Статистика токенов (v0.42+) |
| `cost` | `float \| None` | Стоимость в USD (v0.42+) |
| `processing_time_sec` | `float \| None` | Время обработки в секундах (v0.42+) |
| `words` | computed | Количество слов |
| `change_percent` | computed | Процент изменения текста |

## Что делает очистка (v0.72+)

Единственная задача: **исправление терминологии по глоссарию**.

| Проблема | Пример | Решение |
|----------|--------|---------|
| Ошибки Whisper | "Формула один", "херболайф" | LLM исправляет по глоссарию |
| Термины Herbalife | "гербалайф", "СВ", "гет тим" | LLM нормализует по контексту |
| Имена людей | "Марк Грюз", "Стэпен Грицани" | LLM исправляет по разделу people |

**Что НЕ делает очистка:**
- Не удаляет слова-паразиты ("ну", "вот", "как бы") — longread/story LLM справляется сам
- Не удаляет повторы и заикания — задача следующих этапов
- Не причёсывает текст — сохраняет авторскую речь as is

## Архитектура очистки (v0.72+)

```
RawTranscript (~70KB контента для 55-мин видео)
       │
       ▼
┌─────────────────┐
│ 1. CHUNKING     │  Разбиение на части ~40K chars
│   (1-2 чанка)   │  (для записей >40K chars, без overlap)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 2. LLM CLEAN    │  Chat API с system/user roles
│    (по частям)  │  (glossary v4.0 как контекст)
│ (claude-haiku)  │  1 задача: терминология
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 3. MERGE        │  Простая конкатенация чанков
│                 │
└────────┬────────┘
         │
         ▼
  CleanedTranscript (output ≈ input, ±2-3%)
```

## Глоссарий как контекст LLM

**Изменение в v0.22:** Глоссарий передаётся в LLM как контекст вместо regex-замен.

### Почему LLM вместо Regex

| Аспект | Regex (старый подход) | LLM с глоссарием (новый) |
|--------|----------------------|--------------------------|
| Распознавание | Только точные совпадения | По смыслу и звучанию |
| "херболайф" | Не найдёт | Распознает как "Herbalife" |
| "формула первая" | Не найдёт | Поймёт из description |
| "супер визор" | Не найдёт | По контексту роли |
| Поддержка | Добавлять вариации | LLM догадается сам |

### Структура промпта

```
┌────────────────────────┐
│ System prompt          │  — инструкции по терминологии
│ (cleaner_system.md)    │  — правила работы с глоссарием
└────────────────────────┘
┌────────────────────────┐
│ User prompt            │
│ ┌──────────────────┐   │
│ │ <glossary>       │   │  — glossary.yaml полностью
│ │ ...              │   │
│ │ </glossary>      │   │
│ ├──────────────────┤   │
│ │ <input>          │   │  — транскрипт для очистки
│ │ ...              │   │
│ │ </input>         │   │
│ └──────────────────┘   │
└────────────────────────┘
```

### Что модель делает с глоссарием

Глоссарий v4.0 — семантический формат. Для каждого термина:
- `canonical` — правильное написание
- `description` — смысл термина, сокращения, произношение (главный ориентир)
- `whisper_errors` — известные неочевидные ошибки транскрибации (подсказки)
- `context` — пример употребления

Раздел `people` содержит имена ключевых людей (лидеры, амбассадоры) с щедро заполненным `whisper_errors`.

LLM использует эту информацию для:
1. Распознавания терминов по `description` и смыслу
2. Использования `whisper_errors` как подсказок для сложных случаев
3. Исправления искажённых имён из раздела `people`

### Примеры распознавания

```
"херболайф" → "Herbalife"          (по description + звучанию)
"формула первая" → "Формула 1"     (по описанию из description)
"супер визор" → "Супервайзер"      (по whisper_errors)
"генты" → "ГЕТ"                    (из whisper_errors)
"Марк Грюз" → "Марк Хьюз"         (из people, whisper_errors)
"Стэпен Грицани" → "Стефан Грациани" (из people, whisper_errors)
```

## Текущие параметры

| Параметр | Значение | Описание |
|----------|----------|----------|
| `CLEANER_MODEL` | claude-haiku-4-5 | Модель для очистки (v0.65+, env variable) |
| `CHUNK_SIZE_CHARS` | 40000 | Размер одной части (v0.65+) |
| `CHUNK_OVERLAP_CHARS` | 0 | Без overlap (v0.72+) |
| `SMALL_TEXT_THRESHOLD` | 40000 | Порог для включения chunking (v0.65+) |
| `temperature` | 0.0 | Детерминированный вывод |

## Выбор модели

По умолчанию используется `claude-haiku-4-5` (v0.65+, ранее claude-sonnet, см. [ADR-014](../decisions/014-haiku-default-cleaning.md)). Исторически тестировались локальные модели:

| Модель | Reduction на 3KB | Reduction на 6KB | Статус |
|--------|------------------|------------------|--------|
| gemma2:9b | 18.0% | 19.7% | Стабильна |
| mistral:7b-instruct | 18.4% | 71.4% | Нестабильна |
| phi3:14b | 48.1% | — | Суммаризирует |
| qwen2.5:14b | — | 85% | Суммаризирует |

**Критерии выбора:**
- Minimal change (terminology-only: ±2-3%)
- Стабильность на разных размерах чанков
- Качество русского языка

---

## Chat API с system/user roles

Используем Chat API с разделением на роли:
- `system` — инструкции по терминологии
- `user` — глоссарий + транскрипт для обработки

```python
messages = [
    {"role": "system", "content": system_prompt},
    {"role": "user", "content": user_template.format(
        glossary=glossary_text,
        transcript=chunk,
    )},
]
result = await ai_client.chat(messages, model=settings.cleaner_model, temperature=0.0)
```

## Ожидаемые показатели (v0.72+)

При глоссарной подстановке output ≈ input. Ожидаемое изменение: **±2-3%** (разница в длине заменённых терминов).

| Порог | Уровень | Значение |
|-------|---------|----------|
| >10% reduction (chunk) | WARNING | Модель могла удалить контент |
| >25% reduction (chunk) | ERROR + fallback | Модель суммаризировала, используется оригинал |
| >15% reduction (итого) | WARNING | Возможная потеря контента |
| >25% reduction (итого) | ERROR | Вероятная суммаризация |
| >5% growth | WARNING | Модель могла добавить контент |

## Валидация результата

Сервис автоматически проверяет результат очистки на **двух уровнях**:

### 1. Валидация каждого чанка

После обработки каждого чанка проверяется:
- **Reduction >25%** — модель вероятно суммаризировала
- **Кириллица <50%** — модель переключилась на английский

При провале валидации — **fallback на оригинальный текст** (лучше без замен, чем потерять контент).

### 2. Валидация итогового результата

```
INFO:  Cleaning complete: 60000 -> 59500 chars (0.8% reduction)  ← OK
WARN:  High reduction: 16% - possible content loss               ← Проверить
ERROR: Suspicious reduction: 30% - likely summarization           ← Баг!
WARN:  Text grew by 6.0% - model may have added content          ← Проверить
```

## Тестирование

```bash
cd backend
python -m app.services.cleaner
```

Тесты проверяют: загрузку glossary_text, загрузку промптов с placeholder'ами, полную очистку с LLM.

---

## Связанные файлы

- **Stage:** [backend/app/services/stages/clean_stage.py](../../backend/app/services/stages/clean_stage.py)
- **Сервис:** [backend/app/services/cleaner.py](../../backend/app/services/cleaner.py)
- **Промпты (v0.30+):**
  - [config/prompts/cleaning/system.md](../../config/prompts/cleaning/system.md) — системный промпт
  - [config/prompts/cleaning/user.md](../../config/prompts/cleaning/user.md) — пользовательский шаблон
- **Глоссарий:** [config/glossary.yaml](../../config/glossary.yaml)
- **Модели:** [backend/app/models/schemas.py](../../backend/app/models/schemas.py) — `CleanedTranscript`, `TokensUsed`
- **AI клиенты:** [backend/app/services/ai_clients/](../../backend/app/services/ai_clients/)
- **Исследование:** [docs/research/llm-transcript-cleaning-guide.md](../research/llm-transcript-cleaning-guide.md)
