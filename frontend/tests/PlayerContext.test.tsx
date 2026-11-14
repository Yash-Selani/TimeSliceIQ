import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest';
import { act, render, renderHook, screen } from '@testing-library/react';
import { PlayerProvider, usePlayerContext } from '../src/contexts/PlayerContext';
import { useYouTubePlayer, loadYouTubeIFrameAPI } from '../src/hooks/useYouTubePlayer';

describe('PlayerContext and useYouTubePlayer', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('throws informative error when usePlayerContext is used outside PlayerProvider', () => {
    // Suppress console.error in React for boundary test
    const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

    expect(() => {
      renderHook(() => usePlayerContext());
    }).toThrow(/usePlayerContext must be used within a <PlayerProvider>/);

    consoleSpy.mockRestore();
  });

  it('provides player state and seekTo inside PlayerProvider', () => {
    const TestConsumer = () => {
      const { isReady, currentTime, duration, isPlaying, seekTo } = usePlayerContext();
      return (
        <div>
          <span data-testid="ready">{isReady ? 'READY' : 'NOT_READY'}</span>
          <span data-testid="time">{currentTime}</span>
          <span data-testid="duration">{duration}</span>
          <span data-testid="playing">{isPlaying ? 'PLAYING' : 'PAUSED'}</span>
          <button onClick={() => seekTo(42, true)}>Seek</button>
        </div>
      );
    };

    render(
      <PlayerProvider videoId="mockVideo123">
        <TestConsumer />
      </PlayerProvider>,
    );

    expect(screen.getByTestId('ready')).toHaveTextContent('NOT_READY');
    expect(screen.getByTestId('time')).toHaveTextContent('0');
    expect(screen.getByTestId('playing')).toHaveTextContent('PAUSED');

    // Test optimistic seekTo
    const seekBtn = screen.getByRole('button', { name: 'Seek' });
    act(() => {
      seekBtn.click();
    });

    expect(screen.getByTestId('time')).toHaveTextContent('42');
  });

  it('useYouTubePlayer handles optimistic seekTo and boundary checks', () => {
    const { result } = renderHook(() => useYouTubePlayer({ videoId: 'test123' }));

    expect(result.current.currentTime).toBe(0);
    expect(result.current.isPlaying).toBe(false);

    act(() => {
      result.current.seekTo(125, true);
    });

    expect(result.current.currentTime).toBe(125);

    // Negative numbers clamped to 0
    act(() => {
      result.current.seekTo(-10, false);
    });

    expect(result.current.currentTime).toBe(0);
  });

  it('loadYouTubeIFrameAPI loads script idempotently', async () => {
    const promise1 = loadYouTubeIFrameAPI();
    const promise2 = loadYouTubeIFrameAPI();

    expect(promise1).toBe(promise2);
  });
});
