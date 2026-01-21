/**
 * File utility functions for media type detection.
 */

export const AUDIO_EXTENSIONS = ['mp3', 'wav', 'm4a', 'flac', 'aac', 'ogg'];
export const VIDEO_EXTENSIONS = ['mp4', 'mkv', 'avi', 'mov', 'webm'];

/**
 * Check if filename is an audio file by extension.
 */
export function isAudioFile(filename: string): boolean {
  const ext = filename.split('.').pop()?.toLowerCase() ?? '';
  return AUDIO_EXTENSIONS.includes(ext);
}

/**
 * Check if filename is a video file by extension.
 */
export function isVideoFile(filename: string): boolean {
  const ext = filename.split('.').pop()?.toLowerCase() ?? '';
  return VIDEO_EXTENSIONS.includes(ext);
}
