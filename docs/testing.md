---
doc_type: how-to
status: active
updated: 2026-01-24
audience: [developer, ai-agent]
tags:
  - testing
  - deployment
---

# Тестирование

Руководство по тестированию модулей локально и на сервере.

---

## Локальное тестирование модулей

### Настройка окружения (macOS)

На macOS нельзя устанавливать пакеты в системный Python. Используй виртуальное окружение:

```bash
cd backend

# Создать виртуальное окружение (один раз)
python3 -m venv .venv

# Активировать окружение
source .venv/bin/activate

# Установить зависимости
pip install -r requirements.txt

# Запустить тесты модуля
python -m app.services.parser
python -m app.services.saver

# Деактивировать (по завершении)
deactivate
```

### Встроенные тесты модулей

Многие модули содержат тесты в блоке `if __name__ == "__main__"`. Для их запуска:

```bash
cd backend
source .venv/bin/activate

# Тесты парсера
python -m app.services.parser

# Тесты saver (требует asyncio)
python -m app.services.saver
```

### Проверка синтаксиса без запуска

Быстрая проверка Python-файлов без выполнения:

```bash
python3 -m py_compile backend/app/services/parser.py
python3 -m py_compile backend/app/models/schemas.py
```

### Изолированные тесты (без Settings)

Если тесты требуют Settings, но локально нет `.env`, можно тестировать логику изолированно:

```bash
cd backend
source .venv/bin/activate
python3 -c "
from app.models.schemas import ContentType, EventCategory

# Test enums
assert ContentType.EDUCATIONAL.value == 'educational'
assert EventCategory.REGULAR.value == 'regular'
print('Enums: OK')

# Test regex patterns
from app.services.parser import OFFSITE_LEADERSHIP_PATTERN
match = OFFSITE_LEADERSHIP_PATTERN.match('Антоновы (Дмитрий и Юлия).mp4')
assert match is not None
print('Patterns: OK')
"
```

### Структура тестов в модулях

При добавлении тестов в модуль используй этот шаблон:

```python
if __name__ == "__main__":
    """Run tests when executed directly."""
    import sys

    def test_example():
        """Test description."""
        print("Test: description...", end=" ")
        # ... тест ...
        print("OK")

    tests = [test_example]

    failed = 0
    for test in tests:
        try:
            test()
        except AssertionError as e:
            print(f"FAILED: {e}")
            failed += 1
        except Exception as e:
            print(f"ERROR: {e}")
            failed += 1

    print(f"\n{'All tests passed!' if failed == 0 else f'{failed} test(s) failed.'}")
    sys.exit(failed)
```

---

## Тестирование на сервере

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
| Chunker | `chunk_by_h2` | utils/h2_chunker.py |
| Summarizer | `VideoSummarizer` | summarizer.py |

> **v0.26:** Chunker теперь детерминированный (`chunk_by_h2`), не использует LLM.

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
