# Этап 2: Transcribe (Whisper)

[< Назад: Parse](01-parse.md) | [Обзор Pipeline](README.md) | [Далее: Clean >](03-clean.md)

---

## Назначение

Преобразование аудио в текст с сохранением временных меток сегментов.

## Инструмент

**faster-whisper-server** — REST API сервер для транскрипции, развёрнутый на TrueNAS.

| Параметр | Значение |
|----------|----------|
| API URL | Конфигурируется в `settings.whisper_url` |
| Модель | large-v3 (предзагружена) |
| GPU | RTX 5070 Ti |

## Архитектура

Транскрибация выполняется через `AIClient` — асинхронный HTTP клиент с retry логикой.

```
WhisperTranscriber
        │
        ▼
    AIClient (httpx)
        │
        ▼
  Whisper HTTP API
```

## Конфигурация

```python
# backend/app/config.py
class Settings(BaseSettings):
    whisper_url: str = "http://192.168.1.152:9000"
    whisper_language: str = "ru"
    llm_timeout: int = 300  # 5 минут (общий таймаут)

# Для транскрибации используется увеличенный таймаут 600 сек (10 минут)
```

## Retry логика

AIClient автоматически повторяет запросы при сетевых ошибках:

```python
RETRY_DECORATOR = retry(
    stop=stop_after_attempt(3),           # 3 попытки
    wait=wait_exponential(multiplier=1, min=4, max=60),  # 4-60 сек между попытками
    retry=retry_if_exception_type((httpx.ConnectError, httpx.TimeoutException)),
)
```

## Модель данных

```python
class TranscriptSegment(BaseModel):
    """Single segment from Whisper transcription."""

    start: float          # Начало в секундах (15.5)
    end: float            # Конец в секундах (18.2)
    text: str             # Текст сегмента

    @computed_field
    @property
    def start_time(self) -> str:
        """Formatted start time (HH:MM:SS)."""
        return self._format_time(self.start)

    @computed_field
    @property
    def end_time(self) -> str:
        """Formatted end time (HH:MM:SS)."""
        return self._format_time(self.end)


class RawTranscript(BaseModel):
    """Raw transcript from Whisper."""

    segments: list[TranscriptSegment]
    language: str                    # Определённый язык
    duration_seconds: float          # Длительность видео
    whisper_model: str               # Использованная модель

    @computed_field
    @property
    def full_text(self) -> str:
        """Full text without timestamps."""
        return " ".join(seg.text for seg in self.segments)

    @computed_field
    @property
    def text_with_timestamps(self) -> str:
        """Text with timestamps for LLM processing."""
        lines = [f"[{seg.start_time}] {seg.text}" for seg in self.segments]
        return "\n".join(lines)
```

**Файл моделей:** [`backend/app/models/schemas.py`](../../backend/app/models/schemas.py)

## Класс WhisperTranscriber

```python
class WhisperTranscriber:
    """Video/audio transcription service using Whisper API."""

    def __init__(self, ai_client: AIClient, settings: Settings):
        """
        Initialize transcriber.

        Args:
            ai_client: AI client for API calls
            settings: Application settings
        """
        self.ai_client = ai_client
        self.settings = settings

    async def transcribe(self, video_path: Path) -> RawTranscript:
        """
        Transcribe video/audio file.

        Args:
            video_path: Path to video/audio file

        Returns:
            RawTranscript with segments and metadata

        Raises:
            FileNotFoundError: If file doesn't exist
            httpx.HTTPStatusError: If API returns error
        """
```

## Пример использования

```python
async with AIClient(settings) as client:
    transcriber = WhisperTranscriber(client, settings)
    transcript = await transcriber.transcribe(Path("video.mp4"))

    print(f"Segments: {len(transcript.segments)}")
    print(f"Duration: {transcript.duration_seconds:.1f}s")
    print(f"Text: {transcript.full_text[:100]}...")
```

## Проверка доступности сервиса

```python
async with AIClient(settings) as client:
    status = await client.check_services()

    if status["whisper"]:
        print("Whisper available")
    else:
        print("Whisper unavailable")
```

## Логирование

Сервис логирует ключевые события:

```
INFO: Starting transcription: video.mp4
INFO: Transcription complete: 42 segments, 125.3s duration
```

## Производительность

| Метрика | Значение |
|---------|----------|
| Модель | large-v3 (предзагружена на сервере) |
| Первый запрос после простоя | ~65 сек (загрузка модели в VRAM) |
| Последующие запросы | ~4-5 сек на 15 сек аудио |
| VRAM | ~3.5 GB |
| Таймаут модели | 5 мин неактивности |

> **Важно:** Первый запрос после простоя сервера будет медленным — модель загружается в GPU память.

## Тестирование

Встроенные тесты запускаются командой:

```bash
python -m backend.app.services.transcriber
```

**Тесты:**
1. Парсинг mock-ответа Whisper API
2. Вычисляемые поля (`start_time`, `end_time`, `text_with_timestamps`)
3. Реальная транскрипция (если Whisper доступен и есть тестовый файл)

---

## Связанные документы

- **Код:** [`backend/app/services/transcriber.py`](../../backend/app/services/transcriber.py)
- **AI клиент:** [`backend/app/services/ai_client.py`](../../backend/app/services/ai_client.py)
- **Модели:** [`backend/app/models/schemas.py`](../../backend/app/models/schemas.py)
- **Конфигурация:** [`backend/app/config.py`](../../backend/app/config.py)
