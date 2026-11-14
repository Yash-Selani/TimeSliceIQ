import React from 'react';
import type { components } from '../../types/api';

export type ErrorCode = components['schemas']['ErrorCode'];

export interface ErrorPreset {
  title: string;
  description: string;
  actionLabel: string;
}

export const ERROR_PRESETS: Record<ErrorCode, ErrorPreset> = {
  INVALID_URL: {
    title: 'Invalid YouTube URL',
    description: 'Please paste a valid YouTube video or shorts link.',
    actionLabel: 'Try another URL',
  },
  NO_CAPTIONS: {
    title: 'No Captions Available',
    description: 'This video does not have subtitles or closed captions.',
    actionLabel: 'Choose another video',
  },
  VIDEO_UNAVAILABLE: {
    title: 'Video Unavailable',
    description: 'This video is private, deleted, or region-restricted.',
    actionLabel: 'Choose another video',
  },
  TRANSCRIPT_BLOCKED: {
    title: 'Transcript Temporarily Blocked',
    description: 'YouTube blocked the automated caption request. Please try again or configure a proxy.',
    actionLabel: 'Retry fetch',
  },
  RATE_LIMITED: {
    title: 'Rate Limit Exceeded',
    description: 'Too many requests. Please wait before submitting again.',
    actionLabel: 'Retry',
  },
  LLM_FAILED: {
    title: 'Synthesis Failed',
    description: 'The AI could not process your question. Please try asking in a different way.',
    actionLabel: 'Retry question',
  },
};

export const DEFAULT_ERROR_PRESET: ErrorPreset = {
  title: 'An Error Occurred',
  description: 'The requested operation could not be completed. Please try again.',
  actionLabel: 'Retry',
};

export interface ErrorStateProps {
  /** Error code from API or custom code */
  code?: ErrorCode | string;
  /** Custom title override */
  title?: string;
  /** Custom description override */
  description?: string;
  /** Custom action button label override */
  actionLabel?: string;
  /** Primary action callback */
  onAction?: () => void;
  /** Alias for onAction */
  onRetry?: () => void;
  /** Duration in seconds for rate limit countdown (defaults to 30) */
  countdownSeconds?: number;
  /** Whether auto-countdown is enabled for RATE_LIMITED (defaults to true) */
  autoCountdown?: boolean;
  /** Optional callback fired when countdown reaches zero */
  onCountdownComplete?: () => void;
  /** Technical or debug details shown in a monospace block */
  technicalDetails?: string;
  /** Additional CSS class */
  className?: string;
  /** Inline style overrides */
  style?: React.CSSProperties;
}

export interface EmptyStateProps {
  /** Headline text (defaults to "NO VIDEO LOADED") */
  headline?: string;
  /** Body description (defaults to "Paste a YouTube URL in the header to index the lecture and begin questioning.") */
  body?: string;
  /** Monospace metadata label (defaults to "STANDBY // 00") */
  statusLabel?: string;
  /** Optional keyboard shortcut or usage hint */
  hint?: string;
  /** Optional slot for interactive actions or controls */
  action?: React.ReactNode;
  /** Additional CSS class */
  className?: string;
  /** Inline style overrides */
  style?: React.CSSProperties;
}

export type LoadingStage = 1 | 2 | 3;
export type LoadingStageIdentifier = LoadingStage | 'captions' | 'indexing' | 'ready';

export interface LoadingStateProps {
  /** Current active stage: 1, 2, 3 or named alias */
  stage?: LoadingStageIdentifier;
  /** Custom stage labels (defaults to the 3 standard stages) */
  stages?: string[];
  /** Optional custom title (defaults to "PIPELINE PROCESSING") */
  title?: string;
  /** Optional status detail text */
  statusMessage?: string;
  /** Whether to render the minimalist wireframe skeleton (defaults to true) */
  showSkeleton?: boolean;
  /** Additional CSS class */
  className?: string;
  /** Inline style overrides */
  style?: React.CSSProperties;
}
