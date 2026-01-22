# ADR-010: Интеграция слайдов презентаций

## Статус

Принято (2025-01-23)

## Контекст

При обработке видеозаписей обучающих мероприятий спикеры часто используют презентации со слайдами. Текст на слайдах содержит структурированную информацию (термины, схемы, таблицы), которая:

1. Не всегда озвучивается устно
2. Содержит точные формулировки (vs. свободная речь)
3. Включает визуальные элементы (графики, диаграммы)

### Мотивация

- **Обогащение лонгрида** — добавление точных формулировок со слайдов
- **Структура** — использование заголовков слайдов для структурирования документа
- **Полнота** — включение информации, которая не была озвучена

### Ограничения

- Claude Vision API поддерживает максимум ~20 изображений за запрос
- Большие PDF-файлы требуют конвертации в изображения
- Base64-кодирование увеличивает размер данных ~33%

## Решение

### 1. Архитектура

Слайды обрабатываются как опциональный шаг в pipeline (v0.55+: работает в обоих режимах):

```
┌──────────────────────────────────────────────────────────────────────┐
│                         Step-by-step Pipeline                         │
│                                                                       │
│   Transcribe → Clean → [SLIDES] → Longread/Story → Summary → Chunk   │
│                            ↓                                          │
│                    (только если есть                                  │
│                     прикреплённые слайды)                            │
└──────────────────────────────────────────────────────────────────────┘
```

### 2. Vision API в ClaudeClient

Расширение метода `chat()` для поддержки multimodal content:

```python
class ClaudeClient(BaseAIClientImpl):
    async def chat(
        self,
        messages: list[dict],
        model: str = None,
        ...
    ) -> ChatResult:
        """
        Support multimodal content in messages.

        Message format for images:
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "Extract text from slides"},
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/jpeg",
                        "data": "base64_encoded_data"
                    }
                }
            ]
        }
        """
```

### 3. PDF конвертация

Утилиты для работы с PDF (`backend/app/utils/pdf_utils.py`):

```python
from app.utils.pdf_utils import pdf_to_images, pdf_page_count

# Получить количество страниц
pages = pdf_page_count(Path("presentation.pdf"))

# Конвертировать в PNG изображения
images = pdf_to_images(
    pdf_path=Path("presentation.pdf"),
    dpi=150,  # разрешение
    max_pages=50  # лимит
)
# Returns: list[tuple[bytes, str]]  # (image_data, "image/png")
```

Используется PyMuPDF (fitz) для высокопроизводительной конвертации.

### 4. Сервис извлечения

`SlidesExtractor` обрабатывает слайды батчами:

```python
class SlidesExtractor:
    def __init__(self, ai_client: ClaudeClient, settings: Settings):
        self.batch_size = 5  # из config/models.yaml

    async def extract(
        self,
        slides: list[SlideInput],
        model: str = "claude-haiku-4-5",
        prompt_overrides: PromptOverrides | None = None,
    ) -> SlidesExtractionResult:
        # 1. Конвертация PDF → images
        # 2. Батчинг по batch_size
        # 3. Vision API запросы
        # 4. Объединение результатов
        # 5. Сбор метрик
```

### 5. Модели данных

```python
class SlideInput(BaseModel):
    """Входные данные слайда."""
    filename: str
    content_type: str  # image/jpeg, image/png, application/pdf
    data: str          # base64 encoded

class SlidesExtractionResult(BaseModel):
    """Результат извлечения текста."""
    extracted_text: str      # markdown формат
    slides_count: int
    chars_count: int
    words_count: int
    tables_count: int        # обнаруженные таблицы
    model: str
    tokens_used: TokensUsed | None
    cost: float | None
    processing_time_sec: float | None
```

### 6. API Endpoint

```python
@router.post("/slides")
async def step_slides(request: StepSlidesRequest) -> StreamingResponse:
    """
    Extract text from presentation slides using Claude Vision.

    Returns SSE stream with progress updates and final result.
    """
```

### 7. Интеграция в Longread/Story

Извлечённый текст передаётся как `slides_text` параметр:

```python
# В LongreadGenerator
async def generate(
    self,
    cleaned_transcript: CleanedTranscript,
    metadata: VideoMetadata,
    slides_text: str | None = None,  # NEW
) -> Longread:
    context = cleaned_transcript.text
    if slides_text:
        context += "\n\n## Дополнительная информация со слайдов\n\n" + slides_text
```

## Конфигурация

### models.yaml

```yaml
slides:
  default: claude-haiku-4-5
  batch_size: 5
  available:
    - id: "claude-haiku-4-5"
      name: "Claude Haiku 4.5"
      description: "Быстрый и дешёвый. Для текста и простых таблиц."
    - id: "claude-sonnet-4-5"
      name: "Claude Sonnet 4.5"
      description: "Баланс. Для сложных схем и графиков."
    - id: "claude-opus-4-5"
      name: "Claude Opus 4.5"
      description: "Максимум качества. Для диаграмм и мелкого текста."
```

### Промпты

```
config/prompts/slides/
├── system.md    # Роль и правила извлечения
└── user.md      # Инструкции по обработке изображений
```

## Ограничения

| Параметр | Лимит | Причина |
|----------|-------|---------|
| Макс. файлов | 50 | Контекст модели |
| Макс. размер файла | 10 MB | Claude API |
| Общий размер | 100 MB | Память браузера |
| Batch size | 5 | Баланс скорость/контекст |

## Frontend интеграция

### Главный экран (v0.52)

- `SlidesAttachment` — кнопка/счётчик в карточке видео
- `SlidesModal` — модалка с drag & drop, превью, валидацией

### Пошаговый режим (v0.53)

- Условный шаг `slides` в pipeline
- `useStepSlides` hook для API вызова
- `SlidesResultView` — отображение результата
- Передача `slides_text` в longread/story

### Архив (v0.54)

- `slides_extraction` сохраняется в `pipeline_results.json`
- Таб "Слайды" в `ArchiveResultsModal`

## Последствия

### Положительные

- **Качество** — лонгриды обогащены структурированной информацией
- **Полнота** — включение неозвученного контента
- **Гибкость** — опциональный шаг, не влияет на существующий pipeline

### Отрицательные

- **Стоимость** — Vision API дороже текстового (Haiku: $1/$5 за 1M)
- **Время** — дополнительный шаг увеличивает время обработки
- **Размер** — base64 увеличивает payload на ~33%

### Мониторинг

Метрики отслеживаются через стандартные поля:
- `tokens_used` — usage от Claude API
- `cost` — расчёт по pricing из models.yaml
- `processing_time_sec` — время обработки
- `tables_count` — количество обнаруженных таблиц (индикатор сложности)

## Связанные документы

- [ADR-006: Cloud Model Integration](006-cloud-model-integration.md) — Claude API
- [ADR-009: Extended Metrics](009-extended-metrics.md) — метрики
- [docs/data-formats.md](../data-formats.md) — формат SlidesExtractionResult
- [docs/api-reference.md](../api-reference.md) — API endpoint
