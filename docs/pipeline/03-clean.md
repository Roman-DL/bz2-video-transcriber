# Этап 3: Clean (LLM + Glossary)

[< Назад: Transcribe](02-transcribe.md) | [Обзор Pipeline](README.md) | [Далее: Chunk >](04-chunk.md)

---

## Назначение

Очистка сырого транскрипта от шума и нормализация терминологии.

## Проблемы сырого транскрипта

| Проблема | Пример | Решение |
|----------|--------|---------|
| Слова-паразиты | "ну", "вот", "как бы", "эээ" | LLM удаляет |
| Отвлечения | "кстати, вчера я..." | LLM удаляет |
| Ошибки Whisper | "Формула один" | Глоссарий исправляет |
| Термины Herbalife | "гербалайф" | Глоссарий нормализует |

## Двухэтапная очистка

```
RawTranscript
     │
     ▼
┌─────────────────┐
│ 3a. GLOSSARY    │  Быстрая замена по словарю
│    (Python)     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 3b. LLM CLEAN   │  Удаление паразитов и отвлечений
│    (Ollama)     │
└────────┬────────┘
         │
         ▼
  CleanedTranscript
```

## Класс TranscriptCleaner

```python
class TranscriptCleaner:
    """Transcript cleaning service using glossary and Ollama LLM."""

    def __init__(self, ai_client: AIClient, settings: Settings):
        """
        Initialize cleaner.

        Args:
            ai_client: AI client for LLM calls
            settings: Application settings
        """
        self.ai_client = ai_client
        self.settings = settings
        self.prompt_template = load_prompt("cleaner", settings)
        self.glossary = load_glossary(settings)

    async def clean(
        self,
        raw_transcript: RawTranscript,
        metadata: VideoMetadata,
    ) -> CleanedTranscript:
        """
        Clean raw transcript.

        Args:
            raw_transcript: Raw transcript from Whisper
            metadata: Video metadata (для будущего использования)

        Returns:
            CleanedTranscript with cleaned text and statistics
        """
```

## 3a. Применение глоссария

Метод `_apply_glossary()` выполняет замену терминов:

1. **Сбор замен** — извлекает пары (variation → canonical) из всех категорий
2. **Пропуск метаданных** — игнорирует поля version, date, total_terms (non-list значения)
3. **Сортировка по длине** — длинные вариации первыми (избегает частичных замен)
4. **Регистронезависимый поиск** — `\b{variation}\b` с флагом `re.IGNORECASE`
5. **Запись всех замен** — каждое вхождение добавляется в corrections

```python
def _apply_glossary(self, text: str) -> tuple[str, list[str]]:
    """
    Apply glossary term replacements.

    Returns:
        Tuple of (processed text, list of corrections made)
    """
```

**Почему сортировка по длине?**

Если есть вариации "гет" и "гет тим", нужно обработать "гет тим" первым.
Иначе "гет тим" превратится в "GET тим" (частичная замена).

**Пример corrections:**
```python
# Если "гербалайф" встречается 3 раза в тексте:
corrections = [
    "гербалайф -> Herbalife",
    "гербалайф -> Herbalife",
    "гербалайф -> Herbalife",
]
```

## 3b. LLM Clean (Ollama)

Построение промпта и вызов LLM:

```python
def _build_prompt(self, text: str, metadata: VideoMetadata) -> str:
    """Build cleaning prompt from template."""
    return self.prompt_template.format(transcript=text)
```

> **Примечание:** Параметр `metadata` передаётся для будущего использования (контекст видео), но пока не включается в промпт.

После ответа LLM выполняется `strip()` для удаления whitespace.

## Модель данных

```python
class CleanedTranscript(BaseModel):
    """Cleaned transcript after LLM processing."""

    text: str
    original_length: int
    cleaned_length: int
    corrections_made: list[str] = Field(default_factory=list)
```

**Файл модели:** [`backend/app/models/schemas.py`](../../backend/app/models/schemas.py)

## Пример результата

```python
CleanedTranscript(
    text="Сегодня мы поговорим о Herbalife. Формула 1 — это основной продукт.",
    original_length=164,
    cleaned_length=90,
    corrections_made=["гербалайф -> Herbalife", "формула один -> Формула 1"]
)
```

**Расчёт сокращения:** `100 - (cleaned_length * 100 // original_length)`

## Логирование

Сервис логирует ключевые события:

```
INFO: Cleaning transcript: 1500 chars, 25 segments
DEBUG: Glossary applied: 4 corrections
INFO: Cleaning complete: 1500 -> 980 chars (35% reduction)
```

## Пример использования

```python
async with AIClient(settings) as client:
    cleaner = TranscriptCleaner(client, settings)
    cleaned = await cleaner.clean(raw_transcript, metadata)

    print(f"Original: {cleaned.original_length} chars")
    print(f"Cleaned: {cleaned.cleaned_length} chars")
    print(f"Corrections: {cleaned.corrections_made}")
```

## Структура глоссария

Глоссарий содержит категории терминов:

| Поле | Обязательное | Описание |
|------|--------------|----------|
| `canonical` | Да | Каноническое написание для замены |
| `variations` | Да | Список вариаций для поиска |
| `english` | Нет | Английское название (информационное) |
| `description` | Нет | Описание термина (информационное) |

> Для замены используются только `canonical` и `variations`.
> Записи без этих полей пропускаются.

## Тестирование

Встроенные тесты запускаются командой:

```bash
python -m backend.app.services.cleaner
```

**Тесты:**
1. Загрузка глоссария
2. Применение глоссария (замена терминов)
3. Построение промпта
4. Парсинг mock-транскрипта
5. Полная очистка с LLM (если Ollama доступен)

---

## Связанные документы

- **Код:** [`backend/app/services/cleaner.py`](../../backend/app/services/cleaner.py)
- **AI клиент:** [`backend/app/services/ai_client.py`](../../backend/app/services/ai_client.py)
- **Модели:** [`backend/app/models/schemas.py`](../../backend/app/models/schemas.py)
- **Промпт:** [`config/prompts/cleaner.md`](../../config/prompts/cleaner.md)
- **Глоссарий:** [`config/glossary.yaml`](../../config/glossary.yaml)
