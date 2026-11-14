/**
 * Time formatting utilities for TimeSliceIQ.
 */

/**
 * Formats a duration in seconds into a timestamp string:
 * - Under 1 hour (< 3600s): "MM:SS" (e.g. 75 -> "01:15", 765 -> "12:45")
 * - 1 hour or more (>= 3600s): "HH:MM:SS" (e.g. 3665 -> "01:01:05")
 */
export function secondsToLabel(seconds: number): string {
  const totalSeconds = Math.max(0, Math.floor(isNaN(seconds) || !isFinite(seconds) ? 0 : seconds));
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const secs = totalSeconds % 60;

  const pad = (n: number) => String(n).padStart(2, '0');

  if (hours > 0) {
    return `${pad(hours)}:${pad(minutes)}:${pad(secs)}`;
  }
  return `${pad(minutes)}:${pad(secs)}`;
}

/**
 * Formats seconds into an accessible, natural spoken string for screen readers.
 * Examples:
 * - 0 -> "0 seconds"
 * - 75 -> "1 minute 15 seconds"
 * - 765 -> "12 minutes 45 seconds"
 * - 3600 -> "1 hour"
 * - 3665 -> "1 hour 1 minute 5 seconds"
 */
export function secondsToSpoken(seconds: number): string {
  const totalSeconds = Math.max(0, Math.floor(isNaN(seconds) || !isFinite(seconds) ? 0 : seconds));
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const secs = totalSeconds % 60;

  const parts: string[] = [];

  if (hours > 0) {
    parts.push(`${hours} ${hours === 1 ? 'hour' : 'hours'}`);
  }
  if (minutes > 0) {
    parts.push(`${minutes} ${minutes === 1 ? 'minute' : 'minutes'}`);
  }
  if (secs > 0 || parts.length === 0) {
    parts.push(`${secs} ${secs === 1 ? 'second' : 'seconds'}`);
  }

  return parts.join(' ');
}
