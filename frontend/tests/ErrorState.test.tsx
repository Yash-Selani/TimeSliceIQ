import { act, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import {
  EmptyState,
  ERROR_PRESETS,
  ErrorCode,
  ErrorState,
  LoadingState,
} from '../src/components/ErrorState';

describe('ErrorState Component', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  const errorCodes: ErrorCode[] = [
    'INVALID_URL',
    'NO_CAPTIONS',
    'VIDEO_UNAVAILABLE',
    'TRANSCRIPT_BLOCKED',
    'RATE_LIMITED',
    'LLM_FAILED',
  ];

  it.each(errorCodes)('renders correct content for error code "%s"', (code) => {
    const preset = ERROR_PRESETS[code];
    render(<ErrorState code={code} autoCountdown={false} />);

    expect(screen.getByRole('alert')).toBeInTheDocument();
    expect(screen.getByText(new RegExp(`ERR // ${code}`))).toBeInTheDocument();
    expect(screen.getByText(preset.title)).toBeInTheDocument();
    expect(screen.getByText(preset.description)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: preset.actionLabel })).toBeInTheDocument();
  });

  it('handles custom error overrides and callbacks', () => {
    const handleAction = vi.fn();
    render(
      <ErrorState
        code="INVALID_URL"
        title="Custom Title"
        description="Custom Description"
        actionLabel="Custom Action"
        onAction={handleAction}
        technicalDetails="HTTP 400 Bad Request"
      />
    );

    expect(screen.getByText('Custom Title')).toBeInTheDocument();
    expect(screen.getByText('Custom Description')).toBeInTheDocument();
    expect(screen.getByText('HTTP 400 Bad Request')).toBeInTheDocument();

    const button = screen.getByRole('button', { name: 'Custom Action' });
    fireEvent.click(button);
    expect(handleAction).toHaveBeenCalledTimes(1);
  });

  it('handles RATE_LIMITED auto-countdown timer correctly', () => {
    const onAction = vi.fn();
    const onCountdownComplete = vi.fn();

    render(
      <ErrorState
        code="RATE_LIMITED"
        countdownSeconds={3}
        autoCountdown={true}
        onAction={onAction}
        onCountdownComplete={onCountdownComplete}
      />
    );

    // Initial state: button disabled with countdown
    const button = screen.getByRole('button');
    expect(button).toBeDisabled();
    expect(button).toHaveTextContent(/Retry in 3s/i);

    // Fast-forward 1 second
    act(() => {
      vi.advanceTimersByTime(1000);
    });
    expect(button).toHaveTextContent(/Retry in 2s/i);
    expect(button).toBeDisabled();

    // Fast-forward 2 more seconds
    act(() => {
      vi.advanceTimersByTime(2000);
    });

    // Countdown complete: button enabled
    expect(onCountdownComplete).toHaveBeenCalledTimes(1);
    expect(button).not.toBeDisabled();
    expect(button).toHaveTextContent('Retry');

    // Click enabled button
    fireEvent.click(button);
    expect(onAction).toHaveBeenCalledTimes(1);
  });

  it('renders fallback state for unknown error codes', () => {
    render(<ErrorState code="UNKNOWN_RANDOM_CODE" />);
    expect(screen.getByText('An Error Occurred')).toBeInTheDocument();
    expect(screen.getByText(/The requested operation could not be completed/)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Retry' })).toBeInTheDocument();
  });

  it('contains zero emojis or icons in rendered output', () => {
    const { container } = render(<ErrorState code="INVALID_URL" />);
    // Check text content does not have emojis
    const emojiRegex = /[\u{1F300}-\u{1FAFF}\u{1F600}-\u{1F64F}\u{2600}-\u{26FF}\u{2700}-\u{27BF}]/u;
    expect(emojiRegex.test(container.textContent || '')).toBe(false);
    // Ensure no svg or img icons
    expect(container.querySelector('svg')).toBeNull();
    expect(container.querySelector('img')).toBeNull();
  });
});

describe('EmptyState Component', () => {
  it('renders Swiss minimalist empty state with required headline and body', () => {
    render(<EmptyState />);

    expect(screen.getByRole('status')).toBeInTheDocument();
    expect(screen.getByRole('heading', { level: 2, name: 'NO VIDEO LOADED' })).toBeInTheDocument();
    expect(
      screen.getByText(
        'Paste a YouTube URL in the header to index the lecture and begin questioning.'
      )
    ).toBeInTheDocument();
    expect(screen.getByText(/STATUS: STANDBY/i)).toBeInTheDocument();
  });

  it('renders custom headline, body, and action element', () => {
    render(
      <EmptyState
        headline="CUSTOM EMPTY HEADLINE"
        body="Custom empty body."
        action={<button type="button">Paste from Clipboard</button>}
      />
    );

    expect(screen.getByText('CUSTOM EMPTY HEADLINE')).toBeInTheDocument();
    expect(screen.getByText('Custom empty body.')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Paste from Clipboard' })).toBeInTheDocument();
  });

  it('contains zero emojis or icons in rendered output', () => {
    const { container } = render(<EmptyState />);
    const emojiRegex = /[\u{1F300}-\u{1FAFF}\u{1F600}-\u{1F64F}\u{2600}-\u{26FF}\u{2700}-\u{27BF}]/u;
    expect(emojiRegex.test(container.textContent || '')).toBe(false);
    expect(container.querySelector('svg')).toBeNull();
    expect(container.querySelector('img')).toBeNull();
  });
});

describe('LoadingState Component', () => {
  it('renders standard 3 stages with stage 1 active by default', () => {
    render(<LoadingState stage={1} />);

    expect(screen.getByRole('status')).toBeInTheDocument();
    expect(screen.getByText('1. Fetching captions...')).toBeInTheDocument();
    expect(screen.getByText('2. Indexing concepts...')).toBeInTheDocument();
    expect(screen.getByText('3. Ready')).toBeInTheDocument();

    const progressBar = screen.getByRole('progressbar');
    expect(progressBar).toHaveAttribute('aria-valuenow', '33');
    expect(screen.getByText('STAGE 01 / 03')).toBeInTheDocument();
  });

  it('advances to stage 2 with correct status flags', () => {
    render(<LoadingState stage="indexing" />);

    expect(screen.getByText('STAGE 02 / 03')).toBeInTheDocument();
    const progressBar = screen.getByRole('progressbar');
    expect(progressBar).toHaveAttribute('aria-valuenow', '67');
  });

  it('advances to stage 3 ready state with 100% progress', () => {
    render(<LoadingState stage="ready" />);

    expect(screen.getByText('STAGE 03 / 03')).toBeInTheDocument();
    const progressBar = screen.getByRole('progressbar');
    expect(progressBar).toHaveAttribute('aria-valuenow', '100');
  });

  it('renders wireframe skeleton blocks when showSkeleton is true and hides when false', () => {
    const { rerender } = render(<LoadingState stage={1} showSkeleton={true} />);
    expect(screen.getByText('TRANSCRIPT BUFFER')).toBeInTheDocument();

    rerender(<LoadingState stage={1} showSkeleton={false} />);
    expect(screen.queryByText('TRANSCRIPT BUFFER')).toBeNull();
  });

  it('contains zero emojis or icons in rendered output', () => {
    const { container } = render(<LoadingState stage={2} />);
    const emojiRegex = /[\u{1F300}-\u{1FAFF}\u{1F600}-\u{1F64F}\u{2600}-\u{26FF}\u{2700}-\u{27BF}]/u;
    expect(emojiRegex.test(container.textContent || '')).toBe(false);
    expect(container.querySelector('svg')).toBeNull();
    expect(container.querySelector('img')).toBeNull();
  });
});
