# Рекомендации по транскрипции: борьба с галлюцинациями Whisper

## Контекст

Документ создан на основе практического исследования проблемы галлюцинаций при транскрипции длинных аудиозаписей (55+ минут) на русском языке.

**Окружение:**
- Сервер: TrueNAS SCALE с RTX 5070 Ti (16 GB VRAM)
- Сервис: faster-whisper-server (Docker)
- Язык: русский

## Проблема

При транскрипции длинных аудио модель `Systran/faster-whisper-large-v3` генерирует галлюцинации:

| Тип галлюцинации | Пример | Когда возникает |
|------------------|--------|-----------------|
| Зацикливание | "Пока. Пока. Пока..." до конца файла | Тишина в конце записи |
| Повторы фраз | "да, и, конечно же, фаворит целлюлоз" ×10 | Нечёткая речь, паузы |
| Бессмысленный текст | Случайные слова без связи | После 15-20 минут |

## Решение

### Модель Turbo

**Замена модели на `deepdml/faster-whisper-large-v3-turbo-ct2` решает проблему.**

| Параметр | large-v3 | large-v3-turbo-ct2 |
|----------|----------|---------------------|
| Галлюцинации на длинных файлах | Часто (12-18 мин) | Редко/нет |
| Скорость | Базовая | ~2-3× быстрее |
| Качество русского | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| VRAM | ~3 GB | ~3 GB |

**Проверено:** 55-минутная русскоязычная запись транскрибирована корректно без дополнительных параметров.

## Конфигурация сервера

### Docker Compose для faster-whisper-server

```yaml
services:
  whisper:
    image: fedirz/faster-whisper-server:latest-cuda
    container_name: whisper
    restart: unless-stopped
    
    ports:
      - "9000:8000"
    
    volumes:
      - /mnt/apps-pool/ai/whisper/models:/root/.cache/huggingface
    
    environment:
      # Turbo модель — устойчива к галлюцинациям
      - WHISPER__MODEL=deepdml/faster-whisper-large-v3-turbo-ct2
      - WHISPER__INFERENCE_DEVICE=cuda
      - WHISPER__COMPUTE_TYPE=float16
      - WHISPER__DEFAULT_LANGUAGE=ru
    
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: all
              capabilities: [gpu, compute]
```

### API запрос (базовый)

Turbo модель работает хорошо с дефолтными настройками:

```python
import requests

def transcribe(
    file_path: str,
    language: str = "ru",
    whisper_host: str = "http://100.64.0.1:9000"
) -> str:
    """Транскрибировать аудио/видео файл."""
    url = f"{whisper_host}/v1/audio/transcriptions"
    
    with open(file_path, "rb") as f:
        response = requests.post(
            url,
            files={"file": f},
            data={
                "language": language,
                "response_format": "text",
            },
            timeout=3600,
        )
    
    response.raise_for_status()
    return response.text
```

### API запрос (с дополнительной защитой)

Для особо длинных файлов (2+ часа) или проблемных записей можно добавить параметры:

```python
def transcribe_safe(
    file_path: str,
    language: str = "ru",
    whisper_host: str = "http://100.64.0.1:9000"
) -> str:
    """Транскрибировать с дополнительной защитой от галлюцинаций."""
    url = f"{whisper_host}/v1/audio/transcriptions"
    
    with open(file_path, "rb") as f:
        response = requests.post(
            url,
            files={"file": f},
            data={
                "language": language,
                "response_format": "text",
                "vad_filter": "true",                    # VAD фильтрация тишины
                "condition_on_previous_text": "false",   # Независимые чанки
            },
            timeout=3600,
        )
    
    response.raise_for_status()
    return response.text
```

| Параметр | Что делает | Когда нужен |
|----------|------------|-------------|
| `vad_filter=true` | Silero VAD вырезает тишину | Записи с паузами |
| `condition_on_previous_text=false` | Каждый чанк независим | Очень длинные файлы |

## Доступ к сервису

| Способ | URL |
|--------|-----|
| Web UI | http://192.168.1.152:9000 |
| API (локально) | http://192.168.1.152:9000/v1/audio/transcriptions |
| API (Tailscale) | http://100.64.0.1:9000/v1/audio/transcriptions |
| HTTPS (Traefik) | https://whisper.home |

## Примеры использования

### curl

```bash
# Базовая транскрипция
curl -X POST "http://100.64.0.1:9000/v1/audio/transcriptions" \
  -F "file=@video.mp4" \
  -F "language=ru"

# С таймкодами (SRT)
curl -X POST "http://100.64.0.1:9000/v1/audio/transcriptions" \
  -F "file=@video.mp4" \
  -F "language=ru" \
  -F "response_format=srt" \
  -o subtitles.srt

# С дополнительной защитой
curl -X POST "http://100.64.0.1:9000/v1/audio/transcriptions" \
  -F "file=@video.mp4" \
  -F "language=ru" \
  -F "vad_filter=true" \
  -F "condition_on_previous_text=false"
```

### Python

```python
# Простой пример
transcript = transcribe("meeting.mp4")
print(transcript)

# С JSON ответом (включает таймкоды)
response = requests.post(
    "http://100.64.0.1:9000/v1/audio/transcriptions",
    files={"file": open("video.mp4", "rb")},
    data={"language": "ru", "response_format": "verbose_json"}
)
data = response.json()
for segment in data["segments"]:
    print(f"[{segment['start']:.1f}s] {segment['text']}")
```

## Выбор подхода

```
Транскрипция нужна?
│
├── Файл любой длины, стандартное качество записи
│   └── Turbo + дефолтные настройки ✅
│
├── Очень длинный файл (2+ часа) или много пауз
│   └── Turbo + vad_filter + condition_on_previous_text=false
│
└── Критичное качество (субтитры для публикации)
    └── Turbo + ручная проверка результата
```

## Альтернативные модели (если turbo не подходит)

Список turbo моделей на сервере:

```bash
curl -s http://localhost:9000/v1/models | grep -o '"id":"[^"]*turbo[^"]*"'
```

| Модель | Особенности |
|--------|-------------|
| `deepdml/faster-whisper-large-v3-turbo-ct2` | **Рекомендуемая**, многоязычная |
| `Systran/faster-whisper-large-v3` | Оригинальная, склонна к галлюцинациям |
| `ivrit-ai/whisper-large-v3-turbo-ct2` | Альтернативная turbo |

## Чеклист для проекта с транскрипцией

- [x] Использовать модель `deepdml/faster-whisper-large-v3-turbo-ct2`
- [ ] Установить адекватный timeout (1 час для длинных файлов)
- [ ] Обрабатывать ошибки сети и таймауты
- [ ] (Опционально) Добавить `vad_filter` для проблемных записей

## Что НЕ нужно

| Было в плане | Почему не нужно |
|--------------|-----------------|
| Постобработка галлюцинаций | Turbo не галлюцинирует |
| Детекция повторов | Избыточно |
| Разбиение на чанки | Turbo справляется с длинными файлами |
| Parakeet/NeMo | Не поддерживают русский |

## Ссылки

- [faster-whisper-server](https://github.com/fedirz/faster-whisper-server)
- [faster-whisper](https://github.com/SYSTRAN/faster-whisper)
- [deepdml/faster-whisper-large-v3-turbo-ct2](https://huggingface.co/deepdml/faster-whisper-large-v3-turbo-ct2)

---

**Версия:** 1.1  
**Дата:** 2025-01-11  
**Проверено на:** 55-минутная русскоязычная запись тренинга
