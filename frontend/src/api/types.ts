/**
 * TypeScript types matching backend Pydantic models.
 * Source: backend/app/models/schemas.py
 */

export interface VideoMetadata {
  date: string;
  event_type: string;
  stream: string;
  title: string;
  speaker: string;
  original_filename: string;
  video_id: string;
  source_path: string;
  archive_path: string;
  stream_full: string;
  duration_seconds: number | null;
}

export interface TranscriptSegment {
  start: number;
  end: number;
  text: string;
  start_time: string;
  end_time: string;
}

export interface RawTranscript {
  segments: TranscriptSegment[];
  language: string;
  duration_seconds: number;
  whisper_model: string;
  full_text: string;
  text_with_timestamps: string;
}

export interface CleanedTranscript {
  text: string;
  original_length: number;
  cleaned_length: number;
  corrections_made: string[];
}

export interface TranscriptChunk {
  id: string;
  index: number;
  topic: string;
  text: string;
  word_count: number;
}

export interface TranscriptChunks {
  chunks: TranscriptChunk[];
  total_chunks: number;
  avg_chunk_size: number;
}

export interface VideoSummary {
  summary: string;
  key_points: string[];
  recommendations: string[];
  target_audience: string;
  questions_answered: string[];
  section: string;
  subsection: string;
  tags: string[];
  access_level: number;
}

export interface ServicesHealth {
  whisper: boolean;
  ollama: boolean;
  whisper_url: string;
  ollama_url: string;
}

// Request types
export interface StepParseRequest {
  video_filename: string;
}

export interface StepCleanRequest {
  raw_transcript: RawTranscript;
  metadata: VideoMetadata;
}

export interface StepChunkRequest {
  cleaned_transcript: CleanedTranscript;
  metadata: VideoMetadata;
}

export interface StepSummarizeRequest {
  cleaned_transcript: CleanedTranscript;
  metadata: VideoMetadata;
  prompt_name?: string;
}

export interface StepSaveRequest {
  metadata: VideoMetadata;
  raw_transcript: RawTranscript;
  chunks: TranscriptChunks;
  summary: VideoSummary;
}

// Pipeline step names for UI
export const PIPELINE_STEPS = [
  'parse',
  'transcribe',
  'clean',
  'chunk',
  'summarize',
  'save',
] as const;

export type PipelineStep = (typeof PIPELINE_STEPS)[number];

export const STEP_LABELS: Record<PipelineStep, string> = {
  parse: 'Парсинг метаданных',
  transcribe: 'Транскрипция (Whisper)',
  clean: 'Очистка текста',
  chunk: 'Разбиение на чанки',
  summarize: 'Суммаризация',
  save: 'Сохранение в архив',
};

// Archive types
export interface ArchiveItem {
  title: string;
  speaker: string | null;
}

// Tree structure: year -> event_folder -> items[]
export interface ArchiveResponse {
  tree: Record<string, Record<string, ArchiveItem[]>>;
  total: number;
}
