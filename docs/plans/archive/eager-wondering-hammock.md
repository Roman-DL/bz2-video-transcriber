# План: Исправление потери статистики после v0.58

## Проблема

После v0.58 backend возвращает **camelCase** через `CamelCaseModel` с `by_alias=True`, но frontend типы и компоненты ожидают **snake_case**. Результат: поля не находятся, отображаются как "— симв.", "— слов".

**Пример:**
- Backend отправляет: `{"processingTimeSec": 5.5, "tokensUsed": {...}, "modelName": "claude-sonnet-4-5"}`
- Frontend ожидает: `processing_time_sec`, `tokens_used`, `model_name`
- Результат: `undefined` для всех полей

## Решение

**Обновить frontend на camelCase** — типы и компоненты.

Обоснование:
- TypeScript/JavaScript конвенции предпочитают camelCase
- `PipelineResults` уже использует camelCase для верхнеуровневых ключей
- Одноразовая миграция лучше постоянной трансформации

---

## Файлы для изменения

### 1. [types.ts](frontend/src/api/types.ts) — базовые типы

Изменить snake_case → camelCase во всех интерфейсах:

| Интерфейс | Поля для изменения |
|-----------|-------------------|
| `VideoMetadata` | `event_type` → `eventType`, `original_filename` → `originalFilename`, `video_id` → `videoId`, `source_path` → `sourcePath`, `archive_path` → `archivePath`, `stream_full` → `streamFull`, `duration_seconds` → `durationSeconds`, `content_type` → `contentType`, `event_category` → `eventCategory`, `event_name` → `eventName` |
| `TranscriptSegment` | `start_time` → `startTime`, `end_time` → `endTime` |
| `RawTranscript` | `duration_seconds` → `durationSeconds`, `whisper_model` → `whisperModel`, `full_text` → `fullText`, `text_with_timestamps` → `textWithTimestamps`, `processing_time_sec` → `processingTimeSec` |
| `CleanedTranscript` | `original_length` → `originalLength`, `cleaned_length` → `cleanedLength`, `model_name` → `modelName`, `change_percent` → `changePercent`, `tokens_used` → `tokensUsed`, `processing_time_sec` → `processingTimeSec` |
| `TranscriptChunk` | `word_count` → `wordCount` |
| `TranscriptChunks` | `total_chunks` → `totalChunks`, `avg_chunk_size` → `avgChunkSize`, `model_name` → `modelName`, `total_tokens` → `totalTokens` |
| `LongreadSection` | `source_chunks` → `sourceChunks`, `word_count` → `wordCount` |
| `Longread` | `video_id` → `videoId`, `speaker_status` → `speakerStatus`, `event_type` → `eventType`, `total_sections` → `totalSections`, `total_word_count` → `totalWordCount`, `topic_area` → `topicArea`, `access_level` → `accessLevel`, `model_name` → `modelName`, `tokens_used` → `tokensUsed`, `processing_time_sec` → `processingTimeSec` |
| `Summary` | `video_id` → `videoId`, `key_concepts` → `keyConcepts`, `practical_tools` → `practicalTools`, `topic_area` → `topicArea`, `access_level` → `accessLevel`, `model_name` → `modelName`, `tokens_used` → `tokensUsed`, `processing_time_sec` → `processingTimeSec` |
| `StoryBlock` | `block_number` → `blockNumber`, `block_name` → `blockName` |
| `Story` | `video_id` → `videoId`, `current_status` → `currentStatus`, `event_name` → `eventName`, `main_insight` → `mainInsight`, `time_in_business` → `timeInBusiness`, `time_to_status` → `timeToStatus`, `business_format` → `businessFormat`, `is_family` → `isFamily`, `had_stagnation` → `hadStagnation`, `stagnation_years` → `stagnationYears`, `had_restart` → `hadRestart`, `key_pattern` → `keyPattern`, `access_level` → `accessLevel`, `total_blocks` → `totalBlocks`, `model_name` → `modelName`, `tokens_used` → `tokensUsed`, `processing_time_sec` → `processingTimeSec` |
| `SlidesExtractionResult` | `extracted_text` → `extractedText`, `slides_count` → `slidesCount`, `chars_count` → `charsCount`, `words_count` → `wordsCount`, `tables_count` → `tablesCount`, `tokens_used` → `tokensUsed`, `processing_time_sec` → `processingTimeSec` |

### 2. [StatisticsView.tsx](frontend/src/components/results/StatisticsView.tsx)

Обновить доступ к полям в `buildStepStats()`:
- Строка 100: `processing_time_sec` → `processingTimeSec`
- Строка 101: `whisper_model` → `whisperModel`
- Строка 108: `model_name` → `modelName`
- Строка 113: `processing_time_sec` → `processingTimeSec`
- Строка 116: `tokens_used` → `tokensUsed`
- И аналогично для остальных полей (slides, story, longread, summary)

### 3. Другие компоненты results/

- [LongreadView.tsx](frontend/src/components/results/LongreadView.tsx): `total_word_count`, `tokens_used`, `model_name`
- [SummaryView.tsx](frontend/src/components/results/SummaryView.tsx): `key_concepts`, `practical_tools`, `tokens_used`, `model_name`
- [StoryView.tsx](frontend/src/components/results/StoryView.tsx): `main_insight`, `block_name`, `block_number`, `total_blocks`, `tokens_used`, `model_name`
- [SlidesResultView.tsx](frontend/src/components/results/SlidesResultView.tsx): `slides_count`, `chars_count`, `words_count`, `tables_count`, `extracted_text`, `tokens_used`
- [TranscriptView.tsx](frontend/src/components/results/TranscriptView.tsx): `tokens_used`, `model_name`
- [ChunksView.tsx](frontend/src/components/results/ChunksView.tsx): `model_name`, `word_count`

### 4. [usePipelineProcessor.ts](frontend/src/hooks/usePipelineProcessor.ts)

- `calculateTotals()`: все `processing_time_sec` → `processingTimeSec`, `tokens_used` → `tokensUsed`
- `getStepStats()`: `cleaned_length` → `cleanedLength`, `slides_count` → `slidesCount`, `total_sections` → `totalSections`, `key_concepts` → `keyConcepts`, `total_blocks` → `totalBlocks`, `total_chunks` → `totalChunks`
- Другие места с доступом к полям результатов

### 5. Другие файлы (если TypeScript найдёт ошибки)

- [StepByStep.tsx](frontend/src/components/processing/StepByStep.tsx)
- [ArchiveResultsModal.tsx](frontend/src/components/archive/ArchiveResultsModal.tsx)
- [VideoSummaryView.tsx](frontend/src/components/results/VideoSummaryView.tsx)

---

## Порядок выполнения

1. **Обновить `types.ts`** — все интерфейсы на camelCase
2. **Запустить `npm run build`** — TypeScript покажет все места использования
3. **Исправить компоненты по ошибкам компиляции**
4. **Проверить работу**

---

## Верификация

1. **Step-by-step режим:**
   - Запустить обработку видео
   - Проверить метрики на каждом шаге (модель, время, токены, стоимость)
   - Проверить вкладку "Статистика" после сохранения

2. **Архив:**
   - Открыть результаты существующего видео
   - Проверить отображение всех метрик

3. **Edge cases:**
   - Educational контент (Longread + Summary)
   - Leadership контент (Story)
   - Видео со слайдами
