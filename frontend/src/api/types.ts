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

/**
 * Result from /step/transcribe endpoint.
 * Contains both transcript and path to extracted audio.
 */
export interface TranscribeResult {
  raw_transcript: RawTranscript;
  audio_path: string;
  display_text: string;
}

export interface CleanedTranscript {
  text: string;
  original_length: number;
  cleaned_length: number;
  model_name: string;
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
  model_name: string;
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
  model_name: string;
}

// New models for v0.13 step-by-step pipeline

export interface LongreadSection {
  index: number;
  title: string;
  content: string;
  source_chunks: number[];
  word_count: number;
}

export interface Longread {
  video_id: string;
  title: string;
  speaker: string;
  date: string;
  event_type: string;
  stream: string;
  introduction: string;
  sections: LongreadSection[];
  conclusion: string;
  total_sections: number;
  total_word_count: number;
  section: string;
  subsection: string;
  tags: string[];
  access_level: number;
  model_name: string;
}

export interface Summary {
  video_id: string;
  title: string;
  speaker: string;
  date: string;
  essence: string;
  key_concepts: string[];
  practical_tools: string[];
  quotes: string[];
  insight: string;
  actions: string[];
  section: string;
  subsection: string;
  tags: string[];
  access_level: number;
  model_name: string;
}

export interface PartOutline {
  part_index: number;
  topics: string[];
  key_points: string[];
  summary: string;
}

export interface TranscriptOutline {
  parts: PartOutline[];
  all_topics: string[];
  total_parts: number;
}

export interface ServicesHealth {
  whisper: boolean;
  ollama: boolean;
  whisper_url: string;
  ollama_url: string;
  whisper_include_timestamps: boolean;
}

// Request types
export interface StepParseRequest {
  video_filename: string;
  whisper_model?: string;
}

export interface StepCleanRequest {
  raw_transcript: RawTranscript;
  metadata: VideoMetadata;
  model?: string;
}

export interface StepChunkRequest {
  cleaned_transcript: CleanedTranscript;
  metadata: VideoMetadata;
  model?: string;
}

export interface StepLongreadRequest {
  chunks: TranscriptChunks;
  metadata: VideoMetadata;
  outline?: TranscriptOutline;
  model?: string;
}

export interface StepSummarizeRequest {
  longread: Longread;
  metadata: VideoMetadata;
  model?: string;
}

export interface StepSaveRequest {
  metadata: VideoMetadata;
  raw_transcript: RawTranscript;
  cleaned_transcript: CleanedTranscript;
  chunks: TranscriptChunks;
  longread: Longread;
  summary: Summary;
  audio_path?: string;
}

// Pipeline step names for UI
export const PIPELINE_STEPS = [
  'parse',
  'transcribe',
  'clean',
  'chunk',
  'longread',
  'summarize',
  'save',
] as const;

export type PipelineStep = (typeof PIPELINE_STEPS)[number];

export const STEP_LABELS: Record<PipelineStep, string> = {
  parse: 'Парсинг метаданных',
  transcribe: 'Транскрипция (Whisper)',
  clean: 'Очистка текста',
  chunk: 'Разбиение на чанки',
  longread: 'Генерация лонгрида',
  summarize: 'Генерация конспекта',
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

// Extended archive item with path info for API call
export interface ArchiveItemWithPath extends ArchiveItem {
  year: string;
  eventFolder: string;
  topicFolder: string;
}

// Pipeline results stored in archive
// All blocks are optional to support different pipeline versions
export interface PipelineResults {
  version: string;
  created_at: string;
  metadata: VideoMetadata;
  raw_transcript?: RawTranscript;
  display_text?: string;
  cleaned_transcript?: CleanedTranscript;
  chunks?: TranscriptChunks;
  // Old pipeline: VideoSummary, New pipeline: Summary
  // We treat both as generic object and render as text
  summary?: Record<string, unknown>;
  // New pipeline only
  longread?: Record<string, unknown>;
}

// Response from /archive/results endpoint
export interface PipelineResultsResponse {
  available: boolean;
  message?: string;
  data?: PipelineResults;
}

// Model configuration types
export interface WhisperModelConfig {
  id: string;
  name: string;
  description: string;
}

export interface ClaudeModelConfig {
  id: string;
  name: string;
  description?: string;
}

export type ProviderType = 'local' | 'cloud';

export interface ProviderStatus {
  available: boolean;
  name: string;
}

export interface AvailableModelsResponse {
  ollama_models: string[];
  whisper_models: WhisperModelConfig[];
  claude_models?: ClaudeModelConfig[];
  providers?: {
    local: ProviderStatus;
    cloud: ProviderStatus;
  };
}

export interface DefaultModelsResponse {
  transcribe: string;
  clean: string;
  chunk: string;
  summarize: string;
}

export interface StageConfig {
  chunk_size?: number;
  chunk_overlap?: number;
  small_text_threshold?: number;
  large_text_threshold?: number;
  min_chunk_words?: number;
  target_chunk_words?: number;
  part_size?: number;
  overlap_size?: number;
  min_part_size?: number;
}

export interface ModelConfig {
  context_tokens?: number;
  cleaner?: StageConfig;
  chunker?: StageConfig;
  text_splitter?: StageConfig;
}

export interface ModelsConfigResponse {
  [modelFamily: string]: ModelConfig;
}

// User settings for model selection
export interface ModelSettings {
  transcribe?: string;
  clean?: string;
  chunk?: string;
  summarize?: string;
}
