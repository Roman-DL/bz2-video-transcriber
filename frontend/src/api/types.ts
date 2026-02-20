/**
 * TypeScript types matching backend Pydantic models.
 * Source: backend/app/models/schemas.py
 *
 * v0.58+: All fields use camelCase to match backend CamelCaseModel serialization.
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

// v0.64+: Speaker information from MD transcript
export interface SpeakerInfo {
  namedSpeakers: string[];
  anonymousSpeakers: string[];
  scenario: string; // single | co_speakers | lineup | qa | co_speakers_qa | lineup_qa
}

export interface VideoMetadata {
  date: string;
  eventType: string;
  stream: string;
  title: string;
  speaker: string;
  originalFilename: string;
  videoId: string;
  sourcePath: string;
  archivePath: string;
  streamFull: string;
  durationSeconds: number | null;
  contentType: ContentType;
  eventCategory: EventCategory;
  eventName: string;
  speakerInfo?: SpeakerInfo | null; // v0.64+: from MD transcript
}

export interface TranscriptSegment {
  start: number;
  end: number;
  text: string;
  startTime: string;
  endTime: string;
}

export interface RawTranscript {
  segments: TranscriptSegment[];
  language: string;
  durationSeconds: number;
  whisperModel: string;
  fullText: string;
  textWithTimestamps: string;
  // Metrics (v0.42+) — computed fields serialize to JSON
  chars: number;
  words: number;
  // Optional metrics
  confidence?: number; // 0-1 from Whisper avg_logprob
  processingTimeSec?: number;
}

/**
 * Result from /step/transcribe endpoint.
 * Contains both transcript and path to extracted audio.
 */
export interface TranscribeResult {
  rawTranscript: RawTranscript;
  audioPath?: string | null;
  displayText: string;
}

export interface CleanedTranscript {
  text: string;
  originalLength: number;
  cleanedLength: number;
  modelName: string;
  // Metrics (v0.42+) — computed fields serialize to JSON
  words: number;
  changePercent: number;
  // Optional metrics from LLM
  tokensUsed?: TokensUsed;
  cost?: number;
  processingTimeSec?: number;
}

export interface TranscriptChunk {
  id: string;
  index: number;
  topic: string;
  text: string;
  wordCount: number;
}

export interface TranscriptChunks {
  chunks: TranscriptChunk[];
  totalChunks: number;
  avgChunkSize: number;
  modelName: string;
  // Metrics (v0.42+)
  totalTokens?: number;
  // Description fields (v0.62+)
  description?: string;
  shortDescription?: string;
  describeModelName?: string;
  describeTokensUsed?: TokensUsed;
  describeCost?: number;
  describeProcessingTimeSec?: number;
}

export interface VideoSummary {
  summary: string;
  keyPoints: string[];
  recommendations: string[];
  targetAudience: string;
  questionsAnswered: string[];
  section: string;
  subsection: string;
  tags: string[];
  accessLevel: number;
  modelName: string;
}

// New models for v0.13 step-by-step pipeline

export interface LongreadSection {
  index: number;
  title: string;
  content: string;
  sourceChunks: number[];
  wordCount: number;
}

export interface Longread {
  videoId: string;
  title: string;
  speaker: string;
  speakerStatus: string;
  date: string;
  eventType: string;
  stream: string;
  introduction: string;
  sections: LongreadSection[];
  conclusion: string;
  totalSections: number;
  totalWordCount: number;
  topicArea: string[];
  tags: string[];
  accessLevel: string; // consultant | leader | personal
  modelName: string;
  // Metrics (v0.42+) — computed field
  chars: number;
  // Optional metrics from LLM
  tokensUsed?: TokensUsed;
  cost?: number;
  processingTimeSec?: number;
}

export interface Summary {
  videoId: string;
  title: string;
  speaker: string;
  date: string;
  essence: string;
  keyConcepts: string[];
  practicalTools: string[];
  quotes: string[];
  insight: string;
  actions: string[];
  topicArea: string[];
  tags: string[];
  accessLevel: string; // consultant | leader | personal
  modelName: string;
  // Metrics (v0.42+) — computed fields
  chars: number;
  words: number;
  // Optional metrics from LLM
  tokensUsed?: TokensUsed;
  cost?: number;
  processingTimeSec?: number;
}

// Leadership story (8 blocks structure)
export interface StoryBlock {
  blockNumber: number;
  blockName: string;
  content: string;
}

export interface Story {
  videoId: string;
  names: string;
  currentStatus: string;
  eventName: string;
  date: string;
  mainInsight: string;
  blocks: StoryBlock[];
  timeInBusiness: string;
  timeToStatus: string;
  speed: string; // быстро | средне | долго | очень долго
  businessFormat: string; // клуб | онлайн | гибрид
  isFamily: boolean;
  hadStagnation: boolean;
  stagnationYears: number;
  hadRestart: boolean;
  keyPattern: string;
  mentor: string;
  tags: string[];
  accessLevel: string; // consultant | leader | personal
  related: string[];
  totalBlocks: number;
  modelName: string;
  // Metrics (v0.42+) — computed field
  chars: number;
  // Optional metrics from LLM
  tokensUsed?: TokensUsed;
  cost?: number;
  processingTimeSec?: number;
}

export interface PartOutline {
  partIndex: number;
  topics: string[];
  keyPoints: string[];
  summary: string;
}

export interface TranscriptOutline {
  parts: PartOutline[];
  allTopics: string[];
  totalParts: number;
}

export interface ServicesHealth {
  whisper: boolean;
  ollama: boolean;
  whisperUrl: string;
  ollamaUrl: string;
  whisperIncludeTimestamps: boolean;
}

// ═══════════════════════════════════════════════════════════════════════════
// Request types (sent TO backend)
// Note: Backend uses populate_by_name=True, so camelCase works for requests too
// ═══════════════════════════════════════════════════════════════════════════

export interface StepParseRequest {
  videoFilename: string;
  whisperModel?: string;
}

export interface StepCleanRequest {
  rawTranscript: RawTranscript;
  metadata: VideoMetadata;
  model?: string;
  promptOverrides?: PromptOverrides;
}

export interface StepChunkRequest {
  markdownContent: string;
  metadata: VideoMetadata;
  // Optional content for description generation (v0.62+)
  summary?: Summary;
  longread?: Longread;
  story?: Story;
}

export interface StepLongreadRequest {
  cleanedTranscript: CleanedTranscript;
  metadata: VideoMetadata;
  model?: string;
  promptOverrides?: PromptOverrides;
  slidesText?: string;
}

export interface StepSummarizeRequest {
  cleanedTranscript: CleanedTranscript;
  metadata: VideoMetadata;
  model?: string;
  promptOverrides?: PromptOverrides;
}

export interface StepStoryRequest {
  cleanedTranscript: CleanedTranscript;
  metadata: VideoMetadata;
  model?: string;
  promptOverrides?: PromptOverrides;
  slidesText?: string;
}

export interface StepSaveRequest {
  metadata: VideoMetadata;
  rawTranscript: RawTranscript;
  cleanedTranscript: CleanedTranscript;
  chunks: TranscriptChunks;
  // Educational content (optional)
  longread?: Longread;
  summary?: Summary;
  // Leadership content (optional)
  story?: Story;
  audioPath?: string;
  slidesExtraction?: SlidesExtractionResult;
}

// Pipeline step names for UI
// Note: longread/summarize for educational, story for leadership
// Note: slides step is dynamic (only when slides attached)
export const PIPELINE_STEPS = [
  'parse',
  'transcribe',
  'clean',
  'slides',
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
  slides: 'Извлечение слайдов',
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
  eventType: string;
  midFolder: string;
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
// v0.58+: Uses camelCase for all fields (matches backend PipelineResults model)
export interface PipelineResults {
  version: string;
  createdAt: string;
  contentType?: ContentType;
  metadata: VideoMetadata;
  rawTranscript?: RawTranscript;
  displayText?: string;
  cleanedTranscript?: CleanedTranscript;
  chunks?: TranscriptChunks;
  // Educational content
  longread?: Longread;
  summary?: Summary;
  // Leadership content
  story?: Story;
  // Slides extraction (v0.55+)
  slidesExtraction?: SlidesExtractionResult;
}

/**
 * Result from /api/step/save endpoint.
 * v0.62+: Pure file save, no LLM. Descriptions moved to TranscriptChunks.
 */
export interface SaveResult {
  files: string[];
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
  ollamaModels: string[];
  whisperModels: WhisperModelConfig[];
  claudeModels?: ClaudeModelConfig[];
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
  describe: string;
}

export interface StageConfig {
  chunkSize?: number;
  chunkOverlap?: number;
  smallTextThreshold?: number;
  largeTextThreshold?: number;
  minChunkWords?: number;
  targetChunkWords?: number;
  partSize?: number;
  overlapSize?: number;
  minPartSize?: number;
}

export interface ModelConfig {
  contextTokens?: number;
  cleaner?: StageConfig;
  chunker?: StageConfig;
  textSplitter?: StageConfig;
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
  describe?: string;
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
  contentType: string; // image/jpeg, image/png, application/pdf
  data: string; // base64 encoded
}

/**
 * Result from /api/step/slides endpoint.
 * Source: backend/app/models/schemas.py
 */
export interface SlidesExtractionResult {
  extractedText: string;
  slidesCount: number;
  charsCount: number;
  wordsCount: number;
  tablesCount: number;
  model: string;
  tokensUsed?: TokensUsed;
  cost?: number;
  processingTimeSec?: number;
}

/**
 * Request for /api/step/slides endpoint.
 */
export interface StepSlidesRequest {
  slides: SlideInput[];
  model?: string;
  promptOverrides?: PromptOverrides;
}

// Slides limits for validation
export const SLIDES_LIMITS = {
  MAX_FILES: 50,
  MAX_FILE_SIZE: 10 * 1024 * 1024, // 10 MB
  MAX_TOTAL_SIZE: 100 * 1024 * 1024, // 100 MB
} as const;

// ═══════════════════════════════════════════════════════════════════════════
// Saved Files Types (v0.58+)
// ═══════════════════════════════════════════════════════════════════════════

export interface SavedFiles {
  longread?: string;
  summary?: string;
  story?: string;
  transcript?: string;
  pipelineResults?: string;
}
