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

## 3a. Применение глоссария

Метод `_apply_glossary()` класса `TranscriptCleaner`:

- Собирает замены из всех категорий глоссария
- Сортирует по длине (длинные первыми)
- Регистронезависимый поиск с границами слов (`\b`)
- Возвращает список конкретных замен

**Пример замен:**
```
["гербалайф -> Herbalife", "СВ -> Супервайзер", "формула один -> Формула 1"]
```

## 3b. LLM Clean (Ollama)

```python
class TranscriptCleaner:
    """Сервис очистки транскриптов."""

    def __init__(self, ai_client: AIClient, settings: Settings):
        self.ai_client = ai_client
        self.settings = settings
        self.prompt_template = load_prompt("cleaner", settings)
        self.glossary = load_glossary(settings)

    async def clean(
        self,
        raw_transcript: RawTranscript,
        metadata: VideoMetadata,
    ) -> CleanedTranscript:
        """Очищает транскрипт в два этапа."""
        original_text = raw_transcript.full_text
        original_length = len(original_text)

        # Шаг 1: Применение глоссария
        text_after_glossary, corrections = self._apply_glossary(original_text)

        # Шаг 2: LLM очистка
        prompt = self._build_prompt(text_after_glossary, metadata)
        cleaned_text = await self.ai_client.generate(prompt)

        return CleanedTranscript(
            text=cleaned_text.strip(),
            original_length=original_length,
            cleaned_length=len(cleaned_text),
            corrections_made=corrections,
        )
```

## Модель данных

```python
class CleanedTranscript(BaseModel):
    """Очищенный транскрипт после обработки."""

    text: str                              # Очищенный текст
    original_length: int                   # Длина до очистки (символы)
    cleaned_length: int                    # Длина после очистки
    corrections_made: list[str] = []       # Список замен глоссария
```

**Пример результата:**
```python
CleanedTranscript(
    text="Сегодня мы поговорим о Herbalife. Формула 1 — это основной продукт.",
    original_length=164,
    cleaned_length=90,
    corrections_made=["гербалайф -> Herbalife", "формула один -> Формула 1"]
)
# Сокращение: 46%
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

---

## Связанные документы

- **Код:** [`backend/app/services/cleaner.py`](../../backend/app/services/cleaner.py)
- **Промпт:** [`config/prompts/cleaner.md`](../../config/prompts/cleaner.md)
- **Глоссарий:** [`config/glossary.yaml`](../../config/glossary.yaml)
- **API:** [api-reference.md](../api-reference.md#ollama-api)
