# Fix Missing Metrics in Archive Results

## Problem

При просмотре архивных записей:
1. **Не отображаются метрики** (chars, words, processing_time_sec, tokens_used, cost) — данные не сохраняются в архив
2. **Расхождения layout** между StepByStep и ArchiveResultsModal

## Analysis: Full Comparison

### Header Metrics (шапка карточки)

| Tab | StepByStep | ArchiveResultsModal | Match? |
|-----|------------|---------------------|--------|
| Метаданные | duration | duration | ✅ |
| Транскрипт | processing_time | processing_time | ✅ |
| Очистка | processing_time | processing_time | ✅ |
| Лонгрид | processing_time | processing_time | ✅ |
| Конспект | processing_time | processing_time | ✅ |
| История | total_blocks, speed | total_blocks, speed | ✅ |
| **Чанки** | **(none)** | **total_chunks, avg_chunk_size** | ❌ |

### Component Internal Metrics (внутри компонента View)

| Component | Internal Metrics |
|-----------|------------------|
| RawTranscriptView | `Язык: {language}`, `{chars} симв.`, `{words} слов`, `{confidence}%`, `{whisper_model}` |
| CleanedTranscriptView | `{cleaned_length} симв.`, `{words} слов`, `{change_percent}%`, + ResultFooter |
| LongreadView | `{chars} симв.`, `{total_word_count} слов`, `{reductionPercent}%`, + ResultFooter |
| SummaryView | `{chars} симв.`, `{words} слов`, + ResultFooter |
| StoryView | `{chars} симв.`, `{total_blocks} блоков`, `{processing_time}`, + ResultFooter |
| ChunksView | `{total_chunks} чанков`, `{total_tokens}`, `~{avg_chunk_size}`, `{model_name}` |

### Duplications Found

| Tab | Header | Component Internal | Duplication? |
|-----|--------|-------------------|--------------|
| Чанки | total_chunks, avg_chunk_size | total_chunks, total_tokens, avg_chunk_size, model_name | ❌ **YES** |
| История | total_blocks, speed | chars, total_blocks, processing_time | ⚠️ total_blocks duplicated |

## Solution

### Part 1: Backend — добавить метрики в saver.py

**File:** [saver.py](backend/app/services/saver.py)

#### `_save_pipeline_results_educational()` (lines 250-386)

**RawTranscript** (line 318, после `text_with_timestamps`):
```python
"chars": raw_transcript.chars,
"words": raw_transcript.words,
"confidence": raw_transcript.confidence,
"processing_time_sec": raw_transcript.processing_time_sec,
```

**CleanedTranscript** (line 325, после `model_name`):
```python
"words": cleaned_transcript.words,
"change_percent": cleaned_transcript.change_percent,
"tokens_used": cleaned_transcript.tokens_used.model_dump() if cleaned_transcript.tokens_used else None,
"cost": cleaned_transcript.cost,
"processing_time_sec": cleaned_transcript.processing_time_sec,
```

**Longread** (line 362, после `model_name`):
```python
"chars": longread.chars,
"tokens_used": longread.tokens_used.model_dump() if longread.tokens_used else None,
"cost": longread.cost,
"processing_time_sec": longread.processing_time_sec,
```

**Summary** (line 375, после `model_name`):
```python
"chars": summary.chars,
"words": summary.words,
"tokens_used": summary.tokens_used.model_dump() if summary.tokens_used else None,
"cost": summary.cost,
"processing_time_sec": summary.processing_time_sec,
```

#### `_save_pipeline_results_leadership()` (lines 388-514)

**RawTranscript** (line 452):
```python
"chars": raw_transcript.chars,
"words": raw_transcript.words,
"confidence": raw_transcript.confidence,
"processing_time_sec": raw_transcript.processing_time_sec,
```

**CleanedTranscript** (line 459):
```python
"words": cleaned_transcript.words,
"change_percent": cleaned_transcript.change_percent,
"tokens_used": cleaned_transcript.tokens_used.model_dump() if cleaned_transcript.tokens_used else None,
"cost": cleaned_transcript.cost,
"processing_time_sec": cleaned_transcript.processing_time_sec,
```

**Story** (line 503):
```python
"chars": story.chars,
"tokens_used": story.tokens_used.model_dump() if story.tokens_used else None,
"cost": story.cost,
"processing_time_sec": story.processing_time_sec,
```

### Part 2: Frontend — убрать дублирование метрик

**File:** [ArchiveResultsModal.tsx](frontend/src/components/archive/ArchiveResultsModal.tsx)

#### Fix 1: Chunks header (lines 291-303)

Убрать метрики из шапки, оставить только заголовок (как в StepByStep):

```tsx
{activeTab === 'chunks' && results.chunks && (
  <div className="bg-white border border-gray-200 rounded-lg overflow-hidden h-full flex flex-col">
    <div className="flex items-center justify-between px-4 py-2.5 bg-gray-50 border-b border-gray-100 shrink-0">
      <h3 className="text-sm font-semibold text-gray-900">Чанки</h3>
    </div>
    <div className="p-4 flex-1 overflow-y-auto">
      <ChunksView chunks={results.chunks} />
    </div>
  </div>
)}
```

## Files to Modify

| File | Changes |
|------|---------|
| [saver.py](backend/app/services/saver.py) | Add computed fields and optional metrics to both save methods |
| [ArchiveResultsModal.tsx](frontend/src/components/archive/ArchiveResultsModal.tsx) | Remove duplicate metrics from Chunks header |

## Verification

1. Deploy: `./scripts/deploy.sh`
2. Process a new video through step-by-step
3. Compare both views side by side:
   - **StepByStep**: Processing page → complete all steps → right panel
   - **Archive Modal**: Archive → click on same record
4. Verify for each tab:
   - Header metrics match between views
   - Internal component metrics display correctly (no "—" or "NaN")
   - No duplication between header and component

**Note:** Existing archive records will still have missing metrics until re-processed.
