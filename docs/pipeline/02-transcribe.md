# Этап 2: Transcribe (Whisper)

[< Назад: Parse](01-parse.md) | [Обзор Pipeline](README.md) | [Далее: Clean >](03-clean.md)

---

## Назначение

Преобразование аудио в текст с сохранением временных меток сегментов.

## Инструмент

**faster-whisper-server** — REST API сервер для транскрипции, развёрнутый на TrueNAS.

| Параметр | Значение |
|----------|----------|
| API URL | http://100.64.0.1:9000 |
| Модель | large-v3 (предзагружена) |
| GPU | RTX 5070 Ti |

## Конфигурация

```python
WHISPER_CONFIG = {
    "api_url": "http://100.64.0.1:9000",
    "language": "ru",              # Русский язык
    "response_format": "verbose_json",  # JSON с таймкодами
    "timeout": 600,                # 10 минут для длинных видео
}
```

## Модель данных

```python
@dataclass
class TranscriptSegment:
    """Один сегмент транскрипции от Whisper."""

    start: float          # Начало в секундах (15.5)
    end: float            # Конец в секундах (18.2)
    text: str             # Текст сегмента

    @property
    def start_time(self) -> str:
        """Форматированное время начала (00:00:15)."""
        return self._format_time(self.start)


@dataclass
class RawTranscript:
    """Сырой транскрипт от Whisper."""

    segments: list[TranscriptSegment]
    language: str                    # Определённый язык
    duration_seconds: float          # Длительность видео
    whisper_model: str               # Использованная модель

    @property
    def full_text(self) -> str:
        """Полный текст без тайм-кодов."""
        return " ".join(seg.text for seg in self.segments)

    @property
    def text_with_timestamps(self) -> str:
        """Текст с тайм-кодами для backup."""
        lines = []
        for seg in self.segments:
            lines.append(f"[{seg.start_time}] {seg.text}")
        return "\n".join(lines)
```

## Процесс транскрипции

```python
async def transcribe(video_path: Path, config: dict) -> RawTranscript:
    """Транскрибирует видео через Whisper HTTP API."""

    url = f"{config['api_url']}/v1/audio/transcriptions"

    with open(video_path, "rb") as f:
        response = requests.post(
            url,
            files={"file": f},
            data={
                "language": config["language"],
                "response_format": config["response_format"],
            },
            timeout=config["timeout"]
        )

    response.raise_for_status()
    data = response.json()

    transcript_segments = [
        TranscriptSegment(
            start=seg["start"],
            end=seg["end"],
            text=seg["text"].strip()
        )
        for seg in data.get("segments", [])
    ]

    return RawTranscript(
        segments=transcript_segments,
        language=data.get("language", config["language"]),
        duration_seconds=data.get("duration", 0),
        whisper_model="large-v3"
    )
```

## Проверка доступности сервиса

```python
def check_whisper_available(config: dict) -> bool:
    """Проверить что Whisper сервис доступен."""
    try:
        response = requests.get(
            f"{config['api_url']}/health",
            timeout=5
        )
        return response.text == "OK"
    except requests.RequestException:
        return False
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

---

## Связанные документы

- **Код:** [`backend/app/services/transcriber.py`](../../backend/app/services/transcriber.py)
- **API:** [api-reference.md](../api-reference.md#whisper-api)
