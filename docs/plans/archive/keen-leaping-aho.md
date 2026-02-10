# Фаза 4 (v0.24): Генерация конспекта из CleanedTranscript

## Цель
Переключить SummaryGenerator на работу с `CleanedTranscript` вместо `Longread`. Внедрить 3-компонентную архитектуру промптов.

## Почему это важно
- **Из longread** — "копия копии", теряются детали оригинала
- **Из cleaned** — конспект видит все детали, дополняет (не дублирует) лонгрид

---

## Критические файлы

| Файл | Изменения |
|------|-----------|
| [summary_generator.py](backend/app/services/summary_generator.py) | Переписать под CleanedTranscript, 3 промпта |
| [summarize_stage.py](backend/app/services/stages/summarize_stage.py) | depends_on → ["parse", "clean"] |
| [fallback_factory.py](backend/app/services/pipeline/fallback_factory.py) | Исправить баги section/subsection |
| [schemas.py](backend/app/models/schemas.py) | StepSummarizeRequest → cleaned_transcript |
| config/prompts/summary_*.md | Создать 3 новых файла |

---

## План реализации

### 1. Исправить баги (не ломает API)

**fallback_factory.py:**
- Строки 161-162: `section="Обучение"` → `topic_area=["мотивация"]`
- Строки 164: `access_level=1` → `access_level="consultant"`
- Строки 198-199: `section=longread.section` → `topic_area=longread.topic_area`

**summary_generator.py:**
- Добавить `import re` (используется в строке 209)
- Строки 124-125: `section=longread.section` → удалить (будет генерироваться LLM)

### 2. Создать 3 файла промптов

**config/prompts/summary_system.md** — роль и определение:
```markdown
# System Prompt: Summary Generator
Ты — редактор, создающий конспекты для База Знаний 2.0.
Конспект — навигационный документ для тех, кто УЖЕ слушал тему.
```

**config/prompts/summary_instructions.md** — правила (из docs/template prompts/):
- Типы тем: методическая / философская / смешанная
- Выбор блоков по типу
- Правила извлечения: что включать, что не включать
- Допустимые значения topic_area

**config/prompts/summary_template.md** — JSON структура:
```json
{
  "essence": "2-3 абзаца",
  "key_concepts": ["..."],
  "practical_tools": ["..."],
  "quotes": ["«...»"],
  "insight": "Одно предложение",
  "actions": ["..."],
  "topic_area": ["продажи", "инструменты"],
  "tags": ["тег1"],
  "access_level": "consultant"
}
```

### 3. Переписать SummaryGenerator

```python
class SummaryGenerator:
    def __init__(self, ai_client, settings):
        # 3-компонентная архитектура
        self.system_prompt = load_prompt("summary_system", ...)
        self.instructions = load_prompt("summary_instructions", ...)
        self.template = load_prompt("summary_template", ...)

    async def generate(
        self,
        cleaned_transcript: CleanedTranscript,  # ← ИЗМЕНЕНИЕ
        metadata: VideoMetadata,
    ) -> Summary:
        transcript_text = self._prepare_transcript_text(cleaned_transcript)
        prompt = self._build_prompt(transcript_text, metadata)
        response = await self.ai_client.generate(prompt, ...)
        data = self._parse_response(response)

        # LLM генерирует topic_area и tags
        return Summary(
            topic_area=self._validate_topic_area(data.get("topic_area", [])),
            tags=data.get("tags", []),
            access_level=self._validate_access_level(data.get("access_level")),
            ...
        )

    def _prepare_transcript_text(self, cleaned: CleanedTranscript) -> str:
        """Подготовить cleaned transcript для промпта."""
        text = cleaned.text
        if len(text) > self.max_input_chars:
            text = self._truncate_text(text, self.max_input_chars)
        return text

    def _build_prompt(self, transcript_text, metadata) -> str:
        """Собрать промпт из 3 компонентов."""
        return "\n".join([
            self.system_prompt,
            "---",
            self.instructions,
            "---",
            "## Задание",
            f"**Спикер:** {metadata.speaker}",
            f"**Тема:** {metadata.title}",
            "### Транскрипт",
            transcript_text,
            "### Формат ответа",
            self.template,
        ])
```

### 4. Обновить SummarizeStage

```python
class SummarizeStage(BaseStage):
    name = "summarize"
    depends_on = ["parse", "clean"]  # ← ИЗМЕНЕНИЕ (было: ["parse", "longread"])

    async def execute(self, context: StageContext) -> Summary:
        metadata = context.get_result("parse")
        cleaned_transcript = context.get_result("clean")  # ← ИЗМЕНЕНИЕ
        return await self.generator.generate(cleaned_transcript, metadata)

    def _create_fallback_summary(self, cleaned_transcript, metadata) -> Summary:
        essence = cleaned_transcript.text[:500] + "..."
        return Summary(
            essence=essence,
            topic_area=["мотивация"],
            access_level="consultant",
            ...
        )
```

### 5. Обновить API (breaking change)

**schemas.py** — StepSummarizeRequest:
```python
class StepSummarizeRequest(BaseModel):
    """v0.24: CleanedTranscript вместо Longread."""
    cleaned_transcript: CleanedTranscript  # ← ИЗМЕНЕНИЕ
    metadata: VideoMetadata
    model: str | None = None
```

**step_routes.py** — endpoint /summarize:
- Изменить `request.longread` → `request.cleaned_transcript`

**orchestrator.py** — добавить метод:
```python
async def summarize_from_cleaned(
    self,
    cleaned_transcript: CleanedTranscript,
    metadata: VideoMetadata,
    model: str | None = None,
) -> Summary:
    ...
```

### 6. Добавить fallback метод

**fallback_factory.py:**
```python
def create_summary_from_cleaned(
    self,
    cleaned_transcript: CleanedTranscript,
    metadata: VideoMetadata,
) -> Summary:
    """Fallback summary из cleaned transcript."""
    return Summary(
        essence=cleaned_transcript.text[:500] + "...",
        topic_area=["мотивация"],
        access_level="consultant",
        ...
    )
```

### 7. Обновить тесты

**summary_generator.py** (`if __name__ == "__main__"`):
- Заменить mock Longread на mock CleanedTranscript
- Убрать assertions для section/subsection
- Добавить assertions для topic_area

---

## Порядок выполнения

1. ✅ Исправить баги в fallback_factory.py
2. ✅ Добавить `import re` в summary_generator.py
3. ✅ Создать 3 файла промптов
4. ✅ Переписать SummaryGenerator
5. ✅ Обновить SummarizeStage
6. ✅ Обновить schemas.py (StepSummarizeRequest)
7. ✅ Обновить step_routes.py
8. ✅ Добавить orchestrator.summarize_from_cleaned()
9. ✅ Обновить тесты
10. ✅ Обновить документацию (docs/pipeline/06-summarize.md)
11. ✅ Отметить Фазу 4 в pipeline-optimization-for-rag.md
12. ✅ Обновить CLAUDE.md (версия v0.24)

---

## Документация для обновления

### Обязательные

| Файл | Что обновить |
|------|--------------|
| [docs/pipeline/06-summarize.md](docs/pipeline/06-summarize.md) | **Полная переработка:** архитектура (cleaned вместо longread), модель данных (topic_area вместо section/subsection, access_level как string), промпты (3 файла), диаграмма |
| [docs/research/pipeline-optimization-for-rag.md](docs/research/pipeline-optimization-for-rag.md) | Отметить Фазу 4 как ✅ v0.24, обновить таблицу приоритетов |
| [CLAUDE.md](CLAUDE.md) | Версия v0.24, описание конспекта из cleaned |

### Если есть время

| Файл | Что обновить |
|------|--------------|
| [docs/pipeline/stages.md](docs/pipeline/stages.md) | Пример зависимостей (если упоминается summarize с longread) |
| [docs/data-formats.md](docs/data-formats.md) | Формат summary.md (topic_area вместо section) |

---

## Верификация

1. **Юнит-тесты:**
   ```bash
   cd backend && source .venv/bin/activate
   python -m app.services.summary_generator
   python -m app.services.pipeline.fallback_factory
   ```

2. **Синтаксис:**
   ```bash
   python3 -m py_compile backend/app/services/summary_generator.py
   python3 -m py_compile backend/app/services/stages/summarize_stage.py
   ```

3. **Деплой и тест на сервере:**
   ```bash
   ./scripts/deploy.sh
   # Запустить полный pipeline на тестовом видео educational
   ```

---

## Breaking Changes

**API endpoint `/api/step/summarize`:**
- Было: `{ "longread": Longread, "metadata": VideoMetadata }`
- Стало: `{ "cleaned_transcript": CleanedTranscript, "metadata": VideoMetadata }`

Frontend step-by-step mode нужно обновить, если используется.
