/**
 * TypeScript types matching backend Pydantic models.
 * Source: backend/app/models/schemas.py
 */

// ═══════════════════════════════════════════════════════════════════════════
// Metrics Types (v0.42+)
// ═══════════════════════════════════════════════════════════════════════════

/**
 * Token usage from LLM API.
 * Note: `total` is a computed field in Pydantic and NOT serialized to JSON.
 * Calculate total as `input + output` when needed.
 */
export interface TokensUsed {
  input: number;
  output: number;
}

// Content type determines pipeline flow
export type ContentType = 'educational' | 'leadership';

// Event category determines archive structure
export type EventCategory = 'regular' | 'offsite';

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
  content_type: ContentType;
  event_category: EventCategory;
  event_name: string;
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
  // Metrics (v0.42+) — computed fields serialize to JSON
  chars: number;
  words: number;
  // Optional metrics
  confidence?: number; // 0-1 from Whisper avg_logprob
  processing_time_sec?: number;
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
  // Metrics (v0.42+) — computed fields serialize to JSON
  words: number;
  change_percent: number;
  // Optional metrics from LLM
  tokens_used?: TokensUsed;
  cost?: number;
  processing_time_sec?: number;
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
  // Metrics (v0.42+)
  total_tokens?: number;
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
  speaker_status: string;
  date: string;
  event_type: string;
  stream: string;
  introduction: string;
  sections: LongreadSection[];
  conclusion: string;
  total_sections: number;
  total_word_count: number;
  topic_area: string[];
  tags: string[];
  access_level: string; // consultant | leader | personal
  model_name: string;
  // Metrics (v0.42+) — computed field
  chars: number;
  // Optional metrics from LLM
  tokens_used?: TokensUsed;
  cost?: number;
  processing_time_sec?: number;
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
  topic_area: string[];
  tags: string[];
  access_level: string; // consultant | leader | personal
  model_name: string;
  // Metrics (v0.42+) — computed fields
  chars: number;
  words: number;
  // Optional metrics from LLM
  tokens_used?: TokensUsed;
  cost?: number;
  processing_time_sec?: number;
}

// Leadership story (8 blocks structure)
export interface StoryBlock {
  block_number: number;
  block_name: string;
  content: string;
}

export interface Story {
  video_id: string;
  names: string;
  current_status: string;
  event_name: string;
  date: string;
  main_insight: string;
  blocks: StoryBlock[];
  time_in_business: string;
  time_to_status: string;
  speed: string; // быстро | средне | долго | очень долго
  business_format: string; // клуб | онлайн | гибрид
  is_family: boolean;
  had_stagnation: boolean;
  stagnation_years: number;
  had_restart: boolean;
  key_pattern: string;
  mentor: string;
  tags: string[];
  access_level: string; // consultant | leader | personal
  related: string[];
  total_blocks: number;
  model_name: string;
  // Metrics (v0.42+) — computed field
  chars: number;
  // Optional metrics from LLM
  tokens_used?: TokensUsed;
  cost?: number;
  processing_time_sec?: number;
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
  prompt_overrides?: PromptOverrides;
}

export interface StepChunkRequest {
  markdown_content: string;
  metadata: VideoMetadata;
}

export interface StepLongreadRequest {
  cleaned_transcript: CleanedTranscript;
  metadata: VideoMetadata;
  model?: string;
  prompt_overrides?: PromptOverrides;
}

export interface StepSummarizeRequest {
  cleaned_transcript: CleanedTranscript;
  metadata: VideoMetadata;
  model?: string;
  prompt_overrides?: PromptOverrides;
}

export interface StepStoryRequest {
  cleaned_transcript: CleanedTranscript;
  metadata: VideoMetadata;
  model?: string;
  prompt_overrides?: PromptOverrides;
}

export interface StepSaveRequest {
  metadata: VideoMetadata;
  raw_transcript: RawTranscript;
  cleaned_transcript: CleanedTranscript;
  chunks: TranscriptChunks;
  // Educational content (optional)
  longread?: Longread;
  summary?: Summary;
  // Leadership content (optional)
  story?: Story;
  audio_path?: string;
}

// Pipeline step names for UI
// Note: longread/summarize for educational, story for leadership
export const PIPELINE_STEPS = [
  'parse',
  'transcribe',
  'clean',
  'chunk',
  'longread',
  'summarize',
  'story',
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
  story: 'Генерация истории',
  save: 'Сохранение в архив',
};

// Steps for educational content
export const EDUCATIONAL_STEPS: PipelineStep[] = [
  'parse', 'transcribe', 'clean', 'longread', 'summarize', 'chunk', 'save',
];

// Steps for leadership content
export const LEADERSHIP_STEPS: PipelineStep[] = [
  'parse', 'transcribe', 'clean', 'story', 'chunk', 'save',
];

// Archive types
export interface ArchiveItem {
  title: string;
  speaker: string | null;
  event_type: string;
  mid_folder: string;
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
  content_type?: ContentType; // leadership results have this at top level
  metadata: VideoMetadata;
  raw_transcript?: RawTranscript;
  display_text?: string;
  cleaned_transcript?: CleanedTranscript;
  chunks?: TranscriptChunks;
  // Educational content
  longread?: Longread;
  summary?: Summary;
  // Leadership content
  story?: Story;
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
  longread: string;
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
  longread?: string;
  summarize?: string;
}

// Prompt variants types (v0.33+)
export interface PromptVariantInfo {
  name: string;
  source: 'external' | 'builtin';
  filename: string;
}

export interface ComponentPrompts {
  component: string;
  default: string;
  variants: PromptVariantInfo[];
}

export interface StagePromptsResponse {
  stage: string;
  components: ComponentPrompts[];
}

export interface PromptOverrides {
  system?: string;
  user?: string;
  instructions?: string;
  template?: string;
}

// ═══════════════════════════════════════════════════════════════════════════
// Slides Types (v0.52+)
// ═══════════════════════════════════════════════════════════════════════════

/**
 * Frontend representation of a slide file.
 * Used in InboxCard for slides attachment.
 */
export interface SlideFile {
  id: string;
  name: string;
  size: number;
  type: 'image' | 'pdf';
  file?: File;
  preview?: string; // data URL for image preview
}

/**
 * Backend slide input format for API.
 * Source: backend/app/models/schemas.py
 */
export interface SlideInput {
  filename: string;
  content_type: string; // image/jpeg, image/png, application/pdf
  data: string; // base64 encoded
}

/**
 * Result from /api/step/slides endpoint.
 * Source: backend/app/models/schemas.py
 */
export interface SlidesExtractionResult {
  extracted_text: string;
  slides_count: number;
  chars_count: number;
  words_count: number;
  tables_count: number;
  model: string;
  tokens_used?: TokensUsed;
  cost?: number;
  processing_time_sec?: number;
}

/**
 * Request for /api/step/slides endpoint.
 */
export interface StepSlidesRequest {
  slides: SlideInput[];
  model?: string;
  prompt_overrides?: PromptOverrides;
}

// Slides limits for validation
export const SLIDES_LIMITS = {
  MAX_FILES: 50,
  MAX_FILE_SIZE: 10 * 1024 * 1024, // 10 MB
  MAX_TOTAL_SIZE: 100 * 1024 * 1024, // 100 MB
} as const;
