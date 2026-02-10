# План: Унификация step_routes и pipeline + исправление chunking

## Проблема
1. При пошаговой обработке 55-минутного файла ошибка:
   ```
   Invalid JSON in LLM response: Expecting value: line 37 column 1 (char 3895)
   ```
2. Step_routes и full pipeline используют разную логику — нужна унификация

## Корневая причина ошибки
`ai_client.generate()` в chunker вызывается **без `num_predict`**, используется дефолт (~2048 токенов). Для chunking нужно ~2300+ токенов — output обрезается.

## Текущая архитектура (до унификации)

| Компонент | step_routes | full pipeline |
|-----------|-------------|---------------|
| chunk | orchestrator.chunk() | chunker.chunk_with_outline() |
| longread | AIClient + LongreadGenerator напрямую | через _do_chunk_longread_summarize |
| summarize | AIClient + SummaryGenerator напрямую | через _do_chunk_longread_summarize |
| save | FileSaver напрямую | orchestrator.save() (старый API!) |
| fallback | нет | есть |

## Целевая архитектура (после унификации)

**Step_routes** → **Orchestrator** → **Сервисы**

Вся бизнес-логика (fallback, num_predict, retry) в сервисах. Orchestrator — фасад. Step_routes — только SSE и HTTP.

---

## Изменения в файлах

### 1. backend/app/services/chunker.py

**A) Добавить num_predict (~строки 153, 268):**
```python
estimated_tokens = (part.char_count // 3) * 1.3
num_predict = max(4096, int(estimated_tokens) + 500)
response = await self.ai_client.generate(prompt, model=model, num_predict=num_predict)
```

**B) Добавить fallback в _parse_chunks при JSONDecodeError:**
```python
except json.JSONDecodeError as e:
    logger.warning(f"JSON parse failed: {e}, using fallback")
    return self._create_fallback_part_chunks(text, video_id, index_offset)
```

**C) Добавить метод _create_fallback_part_chunks()** — разбиение по 300 слов.

### 2. backend/app/services/pipeline.py

**A) Добавить метод `longread()`:**
```python
async def longread(
    self,
    chunks: TranscriptChunks,
    metadata: VideoMetadata,
    outline: TranscriptOutline | None = None,
    model: str | None = None,
) -> Longread:
    """Generate longread document from chunks."""
    settings = self._get_settings_with_model(model, "longread")
    async with AIClient(settings) as ai_client:
        generator = LongreadGenerator(ai_client, settings)
        return await generator.generate(chunks, metadata, outline)
```

**B) Добавить метод `summarize_from_longread()`:**
```python
async def summarize_from_longread(
    self,
    longread: Longread,
    metadata: VideoMetadata,
    model: str | None = None,
) -> Summary:
    """Generate summary (конспект) from longread."""
    settings = self._get_settings_with_model(model, "summary")
    async with AIClient(settings) as ai_client:
        generator = SummaryGenerator(ai_client, settings)
        return await generator.generate(longread, metadata)
```

**C) Обновить метод `save()` для нового API:**
```python
async def save(
    self,
    metadata: VideoMetadata,
    raw_transcript: RawTranscript,
    cleaned_transcript: CleanedTranscript,
    chunks: TranscriptChunks,
    longread: Longread,      # <-- Было: summary: VideoSummary
    summary: Summary,         # <-- Добавлено
    audio_path: Path | None = None,
) -> list[str]:
```

**D) Убрать внешний fallback в _do_chunk_longread_summarize** (теперь внутри chunker).

### 3. backend/app/api/step_routes.py

**A) step_longread — использовать orchestrator:**
```python
async def generate_longread() -> Longread:
    return await orchestrator.longread(
        chunks=request.chunks,
        metadata=request.metadata,
        outline=request.outline,
    )
```

**B) step_summarize — использовать orchestrator:**
```python
async def generate_summary() -> Summary:
    return await orchestrator.summarize_from_longread(
        longread=request.longread,
        metadata=request.metadata,
    )
```

**C) step_save — использовать orchestrator:**
```python
files = await orchestrator.save(
    metadata=request.metadata,
    raw_transcript=request.raw_transcript,
    cleaned_transcript=request.cleaned_transcript,
    chunks=request.chunks,
    longread=request.longread,
    summary=request.summary,
    audio_path=audio_path,
)
```

**D) Удалить прямые импорты** AIClient, LongreadGenerator, SummaryGenerator, FileSaver.

---

## Верификация
1. `python3 -m py_compile backend/app/services/chunker.py`
2. `python3 -m py_compile backend/app/services/pipeline.py`
3. `python3 -m py_compile backend/app/api/step_routes.py`
4. `./scripts/deploy.sh`
5. Пошаговая обработка 55-минутного файла → все шаги должны пройти
6. Полный pipeline → должен работать как раньше
7. Проверить логи: `ssh ... 'sudo docker logs bz2-transcriber --tail 50'`
