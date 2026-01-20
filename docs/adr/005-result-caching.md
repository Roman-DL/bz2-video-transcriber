# ADR-005: Версионирование промежуточных результатов

## Статус

Принято (2025-01-20)

## Контекст

При работе с pipeline обработки видео возникают ситуации, когда нужно перезапустить отдельный этап:

1. **Тестирование промптов** — хочется попробовать разные промпты для summarization без полной перегенерации
2. **Смена модели** — сравнить результаты gemma2 vs qwen2.5 для chunking
3. **Исправление ошибок** — LLM сгенерировал плохой результат, нужен re-run
4. **A/B тестирование** — сравнить версии результатов

### Проблемы текущей реализации

- **Нет истории** — при re-run старый результат перезаписывается
- **Потеря контекста** — непонятно, какая модель/промпт использовались
- **Невозможен откат** — нельзя вернуться к предыдущей версии
- **Сложность отладки** — нет способа сравнить версии

## Решение

### 1. Структура кэша

Добавить директорию `.cache/` в архив каждого видео:

```
archive/2025/01.09 ПШ/Video Title/
├── pipeline_results.json    # Текущие результаты (не меняется)
├── longread.md
├── summary.md
├── transcript_*.txt
└── .cache/
    ├── manifest.json        # Версии и метаданные
    ├── transcription/
    │   └── v1.json
    ├── cleaning/
    │   ├── v1.json          # gemma2:9b
    │   └── v2.json          # qwen2.5:14b (re-run)
    ├── chunking/
    │   └── v1.json
    ├── longread/
    │   └── v1.json
    └── summary/
        ├── v1.json
        └── v2.json          # Re-run с новым промптом
```

### 2. Модели данных

#### CacheEntry

```python
class CacheEntry(BaseModel):
    """Одна версия результата этапа."""

    version: int              # 1, 2, 3...
    stage: CacheStageName     # cleaning, chunking, ...
    model_name: str           # gemma2:9b
    created_at: datetime
    input_hash: str           # SHA256 входных данных
    file_path: str            # cleaning/v2.json
    is_current: bool          # Активная версия
    metadata: dict            # Доп. информация (prompt version)
```

#### CacheManifest

```python
class CacheManifest(BaseModel):
    """Манифест всех кэшированных версий."""

    video_id: str
    created_at: datetime
    updated_at: datetime
    entries: dict[str, list[CacheEntry]]  # stage -> versions
    pipeline_version: str
```

### 3. Сервис кэширования

```python
class StageResultCache:
    """Управление версионированным кэшем."""

    async def save(
        self,
        archive_path: Path,
        stage: CacheStageName,
        result: BaseModel,
        model_name: str,
        input_hash: str = "",
    ) -> CacheEntry:
        """Сохранить результат и создать новую версию."""

    async def load(
        self,
        archive_path: Path,
        stage: CacheStageName,
        version: int | None = None,  # None = current
    ) -> dict | None:
        """Загрузить кэшированный результат."""

    async def get_info(self, archive_path: Path) -> CacheInfo:
        """Получить информацию о всех версиях."""

    async def set_current_version(
        self,
        archive_path: Path,
        stage: CacheStageName,
        version: int,
    ) -> bool:
        """Установить активную версию."""
```

### 4. API endpoints

```
GET  /api/cache/{video_id}           # Информация о кэше
POST /api/cache/rerun                # Перезапуск этапа
POST /api/cache/version              # Установка текущей версии
GET  /api/cache/{video_id}/{stage}   # Получить результат
```

#### Пример: перезапуск cleaning с другой моделью

```bash
curl -X POST /api/cache/rerun -d '{
  "video_id": "2025-01-09_ПШ-SV_topic",
  "stage": "cleaning",
  "model": "qwen2.5:14b"
}'
```

Ответ (SSE):
```json
{"type": "progress", "status": "cleaning", "progress": 45}
{"type": "result", "data": {"new_version": 2, "model_name": "qwen2.5:14b"}}
```

### 5. Инвалидация кэша

Кэш инвалидируется при изменении входных данных:

```python
# Вычисление хэша входных данных
input_hash = StageResultCache.compute_hash(raw_transcript)

# Проверка валидности кэша
is_invalid = await cache.invalidate(archive_path, stage, input_hash)
```

Это позволяет:
- Использовать кэш если входные данные не изменились
- Автоматически перегенерировать при изменении предыдущего этапа

## Изменения

### Новые файлы

```
backend/app/models/cache.py              # Pydantic модели
backend/app/services/pipeline/stage_cache.py  # Сервис кэширования
backend/app/api/cache_routes.py          # API endpoints
```

### Обновлённые файлы

```
backend/app/services/pipeline/__init__.py  # Экспорт StageResultCache
backend/app/main.py                        # Подключение cache_routes
backend/app/models/__init__.py             # Экспорт cache моделей
```

## Последствия

### Положительные

- **История версий** — все результаты сохраняются
- **Сравнение** — можно сравнить разные модели/промпты
- **Откат** — легко вернуться к предыдущей версии
- **Отладка** — понятно, что и когда генерировалось
- **Экономия времени** — не нужно перегенерировать весь pipeline

### Отрицательные

- **Место на диске** — каждая версия занимает место
- **Сложность** — нужно управлять версиями
- **Синхронизация** — pipeline_results.json не обновляется автоматически

### Ограничения

- Кэш хранится локально в архиве, не в централизованной БД
- Нет автоматической очистки старых версий
- pipeline_results.json остаётся source of truth для текущего состояния

## Будущие улучшения

1. **UI для версий** — интерфейс сравнения версий в веб-приложении
2. **Автоочистка** — удаление версий старше N дней
3. **Синхронизация** — автообновление pipeline_results.json при смене текущей версии
4. **Diff view** — визуальное сравнение текстовых результатов

## Связанные документы

- [ADR-001: Stage Abstraction](001-stage-abstraction.md)
- [ADR-002: Pipeline Decomposition](002-pipeline-decomposition.md)
- [ADR-004: AI Client Abstraction](004-ai-client-abstraction.md)
- [docs/api-reference.md](../api-reference.md) — описание Cache API
