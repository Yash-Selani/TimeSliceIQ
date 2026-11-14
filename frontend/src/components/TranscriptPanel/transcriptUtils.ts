import type { TranscriptLine } from '@/types/api';

/**
 * Binary search to find the active transcript line index for the given currentTime.
 * Returns the index of the line where start_s <= currentTime < nextLine.start_s.
 * Returns -1 if transcript is empty or currentTime is negative.
 */
export function findActiveTranscriptIndex(
  transcript: readonly TranscriptLine[],
  currentTime: number,
): number {
  if (!transcript || transcript.length === 0 || currentTime < 0) {
    return -1;
  }

  // If time is before the first line, highlight the first line
  if (currentTime < transcript[0].start_s) {
    return 0;
  }

  let low = 0;
  let high = transcript.length - 1;
  let candidate = 0;

  while (low <= high) {
    const mid = Math.floor((low + high) / 2);
    if (transcript[mid].start_s <= currentTime) {
      candidate = mid;
      low = mid + 1; // Try to find a line with start_s closer to currentTime
    } else {
      high = mid - 1;
    }
  }

  return candidate;
}
