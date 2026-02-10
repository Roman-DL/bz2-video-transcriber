# Унификация step_routes и pipeline + исправление ошибки chunking

## Проблема

При пошаговой обработке 55-минутного файла (47K символов) ошибка:
```
Invalid JSON in LLM response: Expecting value: line 37 column 1 (char 3895)
```

**Причина**: `ai_client.generate()` в chunker вызывается без `num_predict`, используется дефолт модели (~2048 токенов). Для chunking нужно ~2300+ токенов - output обрезается.

**Дополнительная проблема**: несогласованность в step_routes - ранние шаги используют orchestrator, поздние создают сервисы напрямую.

---

## Изменения

### 1. chunker.py - исправление ошибки chunking

**Файл**: [backend/app/services/chunker.py](backend/app/services/chunker.py)

**1.1 Добавить динамический расчёт num_predict** (строки ~153, ~268):
```python
# Вычисляем нужное количество токенов на основе размера входного текста
estimated_tokens = (len(part.text) // 3) * 1.3
num_predict = max(4096, int(estimated_tokens) + 500)
response = await self.ai_client.generate(prompt, model=model, num_predict=num_predict)
```

**1.2 Добавить fallback в _parse_chunks()** (строки ~380-385):
- При JSONDecodeError возвращать пустой список вместо выброса исключения
- Вызывающий код создаст fallback chunks

**1.3 Добавить метод _create_fallback_part_chunks()**:
- Простое разбиение текста на чанки по ~300 слов
- Используется когда LLM не вернул валидный JSON

### 2. pipeline.py - новые публичные методы

**Файл**: [backend/app/services/pipeline.py](backend/app/services/pipeline.py)

**2.1 Добавить метод longread()** (после chunk(), ~строка 404):
```python
async def longread(
    self,
    chunks: TranscriptChunks,
    metadata: VideoMetadata,
    outline: TranscriptOutline | None = None,
    model: str | None = None,
) -> Longread:
```
- Создаёт AIClient и LongreadGenerator внутри
- Включает fallback через _create_fallback_longread()

**2.2 Добавить метод summarize_from_longread()**:
```python
async def summarize_from_longread(
    self,
    longread: Longread,
    metadata: VideoMetadata,
    model: str | None = None,
) -> Summary:
```
- Создаёт AIClient и SummaryGenerator внутри
- Включает fallback через _create_fallback_summary_from_longread()

**2.3 Обновить метод save()** (строки 438-464):
- Изменить сигнатуру: `summary: VideoSummary` -> `longread: Longread, summary: Summary`
- saver.py уже принимает Longread + Summary (строки 64-73)

### 3. step_routes.py - унификация через orchestrator

**Файл**: [backend/app/api/step_routes.py](backend/app/api/step_routes.py)

**3.1 step_longread** (строки 380-419):
- Заменить прямое создание AIClient + LongreadGenerator на `orchestrator.longread()`

**3.2 step_summarize** (строки 422-460):
- Заменить прямое создание AIClient + SummaryGenerator на `orchestrator.summarize_from_longread()`

**3.3 step_save** (строки 463-499):
- Заменить прямое создание FileSaver на `orchestrator.save()`

**3.4 Удалить лишние импорты** (строки 37-42):
- `AIClient`, `LongreadGenerator`, `SummaryGenerator`, `FileSaver`

---

## Порядок выполнения

1. **chunker.py** - исправить num_predict и добавить fallback
2. **pipeline.py** - добавить методы longread(), summarize_from_longread(), обновить save()
3. **step_routes.py** - унифицировать через orchestrator

---

## Верификация

1. **Проверка синтаксиса**:
```bash
python3 -m py_compile backend/app/services/chunker.py
python3 -m py_compile backend/app/services/pipeline.py
python3 -m py_compile backend/app/api/step_routes.py
```

2. **Деплой**: `./scripts/deploy.sh`

3. **Тест пошаговой обработки** (через Web UI):
   - Загрузить 55-минутный файл
   - Проверить что chunking проходит без ошибок
   - Проверить что longread и summarize работают через step_routes

4. **Тест полного pipeline**:
   - Запустить полную обработку видео
   - Убедиться что все файлы созданы в архиве

---

## Критичные файлы

| Файл | Изменения |
|------|-----------|
| [chunker.py](backend/app/services/chunker.py) | num_predict, fallback |
| [pipeline.py](backend/app/services/pipeline.py) | longread(), summarize_from_longread(), save() |
| [step_routes.py](backend/app/api/step_routes.py) | унификация через orchestrator |
