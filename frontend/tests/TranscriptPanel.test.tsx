import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import React from 'react';
import {
  TranscriptPanel,
  findActiveTranscriptIndex,
} from '@/components/TranscriptPanel';
import { PlayerContext, PlayerContextValue } from '@/contexts/PlayerContext';
import type { TranscriptLine } from '@/types/api';

describe('findActiveTranscriptIndex', () => {
  const sampleTranscript: TranscriptLine[] = [
    { start_s: 0, text: 'Hello and welcome to the lecture.' },
    { start_s: 14.5, text: 'Today we will cover distributed systems.' },
    { start_s: 32.0, text: 'Let us start with consensus protocols.' },
    { start_s: 60.0, text: 'Paxos and Raft are popular consensus algorithms.' },
    { start_s: 120.0, text: 'In conclusion, state machine replication ensures consistency.' },
  ];

  it('returns -1 for empty transcript or negative time', () => {
    expect(findActiveTranscriptIndex([], 10)).toBe(-1);
    expect(findActiveTranscriptIndex(sampleTranscript, -1)).toBe(-1);
  });

  it('returns 0 if time is at or before first line', () => {
    expect(findActiveTranscriptIndex(sampleTranscript, 0)).toBe(0);
    expect(findActiveTranscriptIndex(sampleTranscript, 5.0)).toBe(0);
  });

  it('finds exact start_s match', () => {
    expect(findActiveTranscriptIndex(sampleTranscript, 14.5)).toBe(1);
    expect(findActiveTranscriptIndex(sampleTranscript, 32.0)).toBe(2);
    expect(findActiveTranscriptIndex(sampleTranscript, 60.0)).toBe(3);
    expect(findActiveTranscriptIndex(sampleTranscript, 120.0)).toBe(4);
  });

  it('finds active line when time falls between lines', () => {
    expect(findActiveTranscriptIndex(sampleTranscript, 20.0)).toBe(1);
    expect(findActiveTranscriptIndex(sampleTranscript, 45.0)).toBe(2);
    expect(findActiveTranscriptIndex(sampleTranscript, 90.0)).toBe(3);
  });

  it('returns the last line index when time is beyond the last line', () => {
    expect(findActiveTranscriptIndex(sampleTranscript, 150.0)).toBe(4);
    expect(findActiveTranscriptIndex(sampleTranscript, 3600.0)).toBe(4);
  });

  it('performs efficiently on large transcripts (1000 lines)', () => {
    const largeTranscript: TranscriptLine[] = Array.from({ length: 1000 }, (_, i) => ({
      start_s: i * 10,
      text: `Lecture segment number ${i}`,
    }));

    // Verify correctness first
    for (let t = 0; t < 500; t += 25) {
      const idx = findActiveTranscriptIndex(largeTranscript, t);
      expect(idx).toBe(Math.min(Math.floor(t / 10), 999));
    }

    // Pure timing loop without assertion overhead
    const start = performance.now();
    for (let t = 0; t < 10000; t += 15) {
      findActiveTranscriptIndex(largeTranscript, t);
    }
    const duration = performance.now() - start;
    expect(duration).toBeLessThan(100);
  });
});

describe('TranscriptPanel component', () => {
  const sampleTranscript: TranscriptLine[] = [
    { start_s: 0, text: 'Introduction to neural networks.' },
    { start_s: 15, text: 'Gradient descent and backpropagation.' },
    { start_s: 45, text: 'Loss functions and optimization.' },
    { start_s: 90, text: 'Convolutional neural networks for vision.' },
  ];

  let mockSeekTo: ReturnType<typeof vi.fn>;
  let playerValue: PlayerContextValue;

  beforeEach(() => {
    mockSeekTo = vi.fn();
    playerValue = {
      isReady: true,
      currentTime: 20,
      duration: 300,
      isPlaying: true,
      seekTo: mockSeekTo,
      containerRef: { current: null },
    };

    // Mock scrollIntoView
    window.HTMLElement.prototype.scrollIntoView = vi.fn();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  const renderWithPlayer = (ui: React.ReactElement, customValue?: Partial<PlayerContextValue>) => {
    return render(
      <PlayerContext.Provider value={{ ...playerValue, ...customValue }}>
        {ui}
      </PlayerContext.Provider>,
    );
  };

  it('renders header micro-label and lines with formatted timestamps', () => {
    renderWithPlayer(<TranscriptPanel transcript={sampleTranscript} />);

    expect(screen.getByText('03 · TRANSCRIPT')).toBeInTheDocument();
    expect(screen.getByText('Auto-scroll: ON')).toBeInTheDocument();

    // Check timestamps
    expect(screen.getByText('00:00')).toBeInTheDocument();
    expect(screen.getByText('00:15')).toBeInTheDocument();
    expect(screen.getByText('00:45')).toBeInTheDocument();
    expect(screen.getByText('01:30')).toBeInTheDocument();

    // Check line text
    expect(screen.getByText('Introduction to neural networks.')).toBeInTheDocument();
    expect(screen.getByText('Gradient descent and backpropagation.')).toBeInTheDocument();
  });

  it('highlights the active line based on currentTime', () => {
    // currentTime = 20, so line at 15s should be active
    renderWithPlayer(<TranscriptPanel transcript={sampleTranscript} />, { currentTime: 20 });

    const activeButtons = screen.getAllByRole('button').filter(
      (btn) => btn.getAttribute('aria-current') === 'time',
    );
    expect(activeButtons).toHaveLength(1);
    expect(activeButtons[0]).toHaveTextContent('Gradient descent and backpropagation.');
  });

  it('calls seekTo when a line is clicked', () => {
    renderWithPlayer(<TranscriptPanel transcript={sampleTranscript} />);

    const lineButton = screen.getByRole('button', {
      name: /01:30: Convolutional neural networks for vision\./i,
    });
    fireEvent.click(lineButton);

    expect(mockSeekTo).toHaveBeenCalledWith(90, true);
  });

  it('toggles auto-scroll when clicking the auto-scroll button', () => {
    renderWithPlayer(<TranscriptPanel transcript={sampleTranscript} />);

    const autoScrollBtn = screen.getByRole('button', { name: /Auto-scroll: ON/i });
    expect(autoScrollBtn).toHaveAttribute('aria-pressed', 'true');

    fireEvent.click(autoScrollBtn);
    expect(screen.getByText('Auto-scroll: OFF')).toBeInTheDocument();
    expect(autoScrollBtn).toHaveAttribute('aria-pressed', 'false');

    fireEvent.click(autoScrollBtn);
    expect(screen.getByText('Auto-scroll: ON')).toBeInTheDocument();
    expect(autoScrollBtn).toHaveAttribute('aria-pressed', 'true');
  });

  it('filters transcript lines in real time by search query', () => {
    renderWithPlayer(<TranscriptPanel transcript={sampleTranscript} />);

    const searchInput = screen.getByLabelText('Filter transcript by text');
    fireEvent.change(searchInput, { target: { value: 'gradient' } });

    expect(screen.getByText('1 match')).toBeInTheDocument();
    expect(screen.getByText('4 total lines')).toBeInTheDocument();

    expect(
      screen.getByRole('button', { name: /Gradient descent and backpropagation/i }),
    ).toBeInTheDocument();
    expect(screen.getByText('Gradient')).toBeInTheDocument(); // <mark> element
    expect(screen.queryByText('Introduction to neural networks.')).not.toBeInTheDocument();

    // Clear search
    const clearButton = screen.getByLabelText('Clear search query');
    fireEvent.click(clearButton);

    expect(screen.queryByText('1 match')).not.toBeInTheDocument();
    expect(screen.getByText('Introduction to neural networks.')).toBeInTheDocument();
  });

  it('displays empty state when search finds no matches', () => {
    renderWithPlayer(<TranscriptPanel transcript={sampleTranscript} />);

    const searchInput = screen.getByLabelText('Filter transcript by text');
    fireEvent.change(searchInput, { target: { value: 'quantum superposition' } });

    expect(screen.getByText('No matches found')).toBeInTheDocument();
  });

  it('displays empty state when transcript is empty', () => {
    renderWithPlayer(<TranscriptPanel transcript={[]} />);

    expect(screen.getByText('No transcript available')).toBeInTheDocument();
  });

  it('responds to custom timesliceiq:seek DOM event', () => {
    renderWithPlayer(<TranscriptPanel transcript={sampleTranscript} />);

    // Dispatch custom event
    const seekEvent = new CustomEvent('timesliceiq:seek', {
      detail: { seconds: 45 },
    });
    window.dispatchEvent(seekEvent);

    expect(window.HTMLElement.prototype.scrollIntoView).toHaveBeenCalled();
  });
});
