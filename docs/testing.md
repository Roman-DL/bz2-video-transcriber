# Тестирование на сервере

Руководство по автоматическому тестированию pipeline-шагов на сервере без веб-интерфейса.

## Важно: пути в контейнере

| Хост (TrueNAS) | Контейнер |
|----------------|-----------|
| `/mnt/main/work/bz2/video/` | `/data/` |
| `/mnt/main/work/bz2/video/inbox/` | `/data/inbox/` |
| `/mnt/main/work/bz2/video/archive/` | `/data/archive/` |

Папка `scripts/` НЕ копируется в образ — только `backend/` как `/app/`.

---

## Базовые операции

```bash
# Через SSH (используя .env.local credentials)
source .env.local && sshpass -p "$DEPLOY_PASSWORD" ssh "${DEPLOY_USER}@${DEPLOY_HOST}" "команда"

# Health check
curl -s http://localhost:8801/health
curl -s http://localhost:8801/health/services

# Список файлов в inbox и архиве
curl -s http://localhost:8801/api/inbox
curl -s http://localhost:8801/api/archive

# Логи контейнера
sudo docker logs bz2-transcriber --tail 50
```

---

## Тестирование pipeline-шагов

Для тестирования сервисов (Cleaner, Chunker, Summarizer) на существующих данных — запускай inline Python в контейнере:

```bash
source .env.local && sshpass -p "$DEPLOY_PASSWORD" ssh "${DEPLOY_USER}@${DEPLOY_HOST}" \
  "echo '$DEPLOY_PASSWORD' | sudo -S docker exec bz2-transcriber python -c \"
import sys
sys.path.insert(0, '/app')
# ... код теста ...
\""
```

### Классы сервисов

| Сервис | Класс | Файл |
|--------|-------|------|
| Cleaner | `TranscriptCleaner` | cleaner.py |
| Chunker | `SemanticChunker` | chunker.py |
| Summarizer | `VideoSummarizer` | summarizer.py |

### Обязательные поля Pydantic-моделей

```python
from datetime import date
from pathlib import Path
from app.models.schemas import RawTranscript, TranscriptSegment, VideoMetadata

# RawTranscript
raw_transcript = RawTranscript(
    segments=[TranscriptSegment(start=0.0, end=1.0, text="...")],
    full_text="...",
    duration_seconds=3300.0,
    language="ru",
    whisper_model="large-v3",
)

# VideoMetadata
metadata = VideoMetadata(
    title="Test",
    event_type="ПШ",
    stream="SV",
    topic="Test",
    speaker="Test",
    date=date.today(),
    original_filename="test.mp4",
    video_id="test123",
    source_path=Path("/data/inbox/test.mp4"),
    archive_path=Path("/data/archive/test"),
)
```

---

## Примеры тестов

### Тест Cleaner

```python
import sys
sys.path.insert(0, '/app')
import asyncio
from datetime import date
from pathlib import Path
from app.config import Settings
from app.services.ai_client import AIClient
from app.services.cleaner import TranscriptCleaner
from app.models.schemas import RawTranscript, TranscriptSegment, VideoMetadata

async def test():
    # Читаем существующий транскрипт
    with open('/data/archive/2025/12.22 ПШ/SV .../transcript_raw.txt', 'r') as f:
        raw_text = f.read()

    print(f'Input: {len(raw_text)} chars')

    settings = Settings()
    async with AIClient(settings) as ai_client:
        cleaner = TranscriptCleaner(ai_client, settings)

        raw_transcript = RawTranscript(
            segments=[TranscriptSegment(start=0.0, end=1.0, text=raw_text)],
            full_text=raw_text,
            duration_seconds=3300.0,
            language='ru',
            whisper_model='large-v3',
        )

        metadata = VideoMetadata(
            title='Test', event_type='ПШ', stream='SV',
            topic='Test', speaker='Test', date=date.today(),
            original_filename='test.mp4', video_id='test123',
            source_path=Path('/data/inbox/test.mp4'),
            archive_path=Path('/data/archive/test'),
        )

        result = await cleaner.clean(raw_transcript, metadata)

        print(f'Output: {len(result.text)} chars')
        reduction = (1 - len(result.text) / len(raw_text)) * 100
        print(f'Reduction: {reduction:.1f}%')

asyncio.run(test())
```

### Тест прямого вызова LLM

Для тестирования промптов без полного pipeline:

```python
import sys
sys.path.insert(0, '/app')
import asyncio
from app.config import Settings
from app.services.ai_client import AIClient

async def test():
    settings = Settings()
    async with AIClient(settings) as ai_client:
        messages = [
            {'role': 'system', 'content': 'Your system prompt here'},
            {'role': 'user', 'content': 'Your user message here'},
        ]
        result = await ai_client.chat(messages, temperature=0.0)
        print(f'Result: {len(result)} chars')
        print(result[:500])

asyncio.run(test())
```

---

## Цикл отладки

1. Внести изменения в код локально
2. Задеплоить: `./scripts/deploy.sh`
3. Запустить тест через inline Python
4. Проверить логи: `sudo docker logs bz2-transcriber --tail 50`
5. Повторить при необходимости

---

## Связанные документы

- [deployment.md](deployment.md) — деплой и конфигурация
- [logging.md](logging.md) — настройка логов
- [pipeline/](pipeline/) — документация этапов обработки
