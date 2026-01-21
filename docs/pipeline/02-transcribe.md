# Этап 2: Transcribe (Whisper)

[< Назад: Parse](01-parse.md) | [Обзор Pipeline](README.md) | [Далее: Clean >](03-clean.md)

---

## Назначение

Преобразование видео в текст с сохранением временных меток сегментов.

## Архитектура

Транскрипция выполняется в два этапа для надёжности:

```
Video (MP4/MKV) или Audio (MP3/WAV/M4A)
       │
       ▼
AudioExtractor (ffmpeg, если видео)
       │
       ▼
Audio (MP3, 128kbps)
       │
       ▼
WhisperTranscriber
       │
       ▼
WhisperClient (httpx)  ← v0.27: отдельный клиент
       │
       ▼
Whisper HTTP API
       │
       ▼
RawTranscript + audio.mp3
```

### Почему извлекаем аудио

Извлечение аудио через ffmpeg перед транскрипцией даёт преимущества:

- **Надёжность** — аудиоформаты стабильнее обрабатываются Whisper
- **Размер** — MP3 ~10% от размера видео (быстрее передаётся по сети)
- **Сохранение** — аудиодорожка сохраняется в архив как `audio.mp3`

## Конфигурация

| Параметр | Описание | Где настраивается |
|----------|----------|-------------------|
| `whisper_url` | URL Whisper API | `backend/app/config.py` |
| `whisper_language` | Язык транскрипции | `backend/app/config.py` |
| `temp_dir` | Папка для временных аудиофайлов | `backend/app/config.py` |

**Таймауты:**
- Извлечение аудио (ffmpeg): 600 сек (10 мин)
- Транскрипция (Whisper): 7200 сек (2 часа)

## Retry логика

AIClient автоматически повторяет запросы при сетевых ошибках:
- 3 попытки
- Экспоненциальная задержка 4-60 сек
- Retry на `ConnectError`, `TimeoutException`

## Модель данных

Транскрипция возвращает `RawTranscript` с сегментами и метаданными.

**Ключевые поля:**
- `segments` — список сегментов с таймкодами
- `duration_seconds` — длительность видео
- `full_text` — весь текст без таймкодов (computed)
- `text_with_timestamps` — текст в формате `[HH:MM:SS] Текст` (computed)

Подробнее: [`backend/app/models/schemas.py`](../../backend/app/models/schemas.py)

## Возвращаемые данные

Метод `transcribe()` возвращает tuple:
1. `RawTranscript` — транскрипция с сегментами
2. `Path` — путь к извлечённому аудиофайлу (для сохранения в архив)

## Производительность

| Метрика | Значение |
|---------|----------|
| Модель | `deepdml/faster-whisper-large-v3-turbo-ct2` |
| Извлечение аудио | ~5-15 сек (зависит от размера видео) |
| Первый запрос после простоя | ~65 сек (загрузка модели в VRAM) |
| Последующие запросы | ~2-3 сек на 15 сек аудио (turbo ~2× быстрее) |
| VRAM | ~3 GB |
| Таймаут модели | 5 мин неактивности |

> **Важно:** Первый запрос после простоя сервера будет медленным — модель загружается в GPU память.

## Галлюцинации Whisper

Модели Whisper склонны к галлюцинациям на длинных аудио — повторяющиеся фразы, зацикливание. Turbo модель (`large-v3-turbo-ct2`) устойчива к этой проблеме.

**Для особо проблемных записей** можно добавить параметры:
- `vad_filter=true` — VAD фильтрация тишины (Silero VAD)
- `condition_on_previous_text=false` — независимые чанки

Подробнее: [docs/research/whisper-recommendations.md](../research/whisper-recommendations.md)

## Логирование

```
INFO: Extracting audio: video.mp4 (500.0 MB) -> video_audio.mp3
INFO: Audio extracted: video_audio.mp3 (45.2 MB)
INFO: Audio extraction took 12.3s
INFO: Transcription complete: 2648 segments, 3307.0s duration
PERF: transcribe | size=500.0MB | duration=3307s | extract=12.3s | whisper=245.6s | total=257.9s
```

## Тестирование

```bash
# Тест AudioExtractor
python -m backend.app.services.audio_extractor

# Тест WhisperTranscriber
python -m backend.app.services.transcriber
```

**Тесты:**
1. Проверка доступности ffmpeg
2. Извлечение аудио из тестового видео
3. Парсинг mock-ответа Whisper API
4. Вычисляемые поля (`start_time`, `end_time`, `text_with_timestamps`)
5. Реальная транскрипция (если Whisper доступен)

---

## Связанные файлы

- [`backend/app/services/audio_extractor.py`](../../backend/app/services/audio_extractor.py) — извлечение аудио
- [`backend/app/services/transcriber.py`](../../backend/app/services/transcriber.py) — транскрипция
- [`backend/app/services/ai_clients/whisper_client.py`](../../backend/app/services/ai_clients/whisper_client.py) — HTTP клиент для Whisper (v0.27+)
- [`backend/app/models/schemas.py`](../../backend/app/models/schemas.py) — модели данных
